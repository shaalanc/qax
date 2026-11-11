"""Generate Playwright (JS) specs from Excel test cases.

Natural-language steps are compiled deterministically into Playwright
calls that use resilient helper functions (``helpers.js``). When selectors
break after an app update, ``qax heal`` runs the embedded agent to repair
the generated code (see the qa-self-healing skill) — never the app code.
"""

from __future__ import annotations

import re
from pathlib import Path

from qax.excel_parser import TestCase

HELPERS_SOURCE = r'''// qax-generated shared Playwright helpers (resilient locator resolution).
// Self-healing target: if selectors break after an app update, improve
// `resolve()` here (or in the specs) via `qax heal`. Only this file and the
// specs may be edited by the healer — never application code.
const { expect } = require('@playwright/test');

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function resolve(page, target) {
  target = String(target).trim().replace(/^["']|["']$/g, '');
  if (!target) throw new Error('empty locator target');
  if (target.startsWith('#') || target.startsWith('.') || target.includes('[')
      || target.startsWith('css=') || target.startsWith('xpath=')) {
    return page.locator(target);
  }
  const strategies = [
    () => page.getByTestId(target),
    () => page.getByRole('button', { name: target, exact: false }),
    () => page.getByRole('link', { name: target, exact: false }),
    () => page.getByLabel(target, { exact: false }),
    () => page.getByPlaceholder(target, { exact: false }),
    () => page.getByText(target, { exact: false }),
    () => page.locator('input[name="' + target + '"]'),
  ];
  for (const make of strategies) {
    try {
      const loc = make();
      if (await loc.count() > 0) return loc;
    } catch (e) { /* try next strategy */ }
  }
  // Fuzzy fallback: the target may be a loose description ("Increment
  // button", "Counter heading") whose words appear in an element's
  // accessible text — a common drift pattern in generated tests.
  const words = target.split(/\W+/).filter(function (w) { return w.length > 2; });
  for (const role of ['button', 'link', 'heading', 'cell', 'listitem']) {
    try {
      const els = page.getByRole(role);
      const n = await els.count();
      for (let i = 0; i < n; i++) {
        const el = els.nth(i);
        try {
          const t = ((await el.innerText()) || '').trim().toLowerCase();
          if (words.some(function (w) { return t.includes(w.toLowerCase()); })) {
            return el;
          }
        } catch (e) { /* skip element */ }
      }
    } catch (e) { /* skip role */ }
  }
  return page.getByText(target, { exact: false });
}

async function open_page(page, url) { await page.goto(url); }
async function click(page, target) { await (await resolve(page, target)).first().click(); }
async function fill(page, target, value) { await (await resolve(page, target)).first().fill(value); }
async function select_option(page, target, value) { await (await resolve(page, target)).first().selectOption(value); }
async function check(page, target) { await (await resolve(page, target)).first().check(); }
async function uncheck(page, target) { await (await resolve(page, target)).first().uncheck(); }
async function clear(page, target) { await (await resolve(page, target)).first().clear(); }
async function hover(page, target) { await (await resolve(page, target)).first().hover(); }
async function press_key(page, target, key) { await (await resolve(page, target)).first().press(key); }
async function press(page, key) { await page.keyboard.press(key); }
async function wait_for(page, target, timeoutMs) {
  await (await resolve(page, target)).first().waitFor({ state: 'visible', timeout: timeoutMs || 10000 });
}
async function assert_visible(page, text) { await expect((await resolve(page, text)).first()).toBeVisible(); }
async function assert_not_visible(page, text) {
  await expect((await resolve(page, text)).first()).toHaveCount(0);
}
async function assert_text_visible(page, text) { await expect(page.getByText(text, { exact: false }).first()).toBeVisible(); }
async function assert_text_not_visible(page, text) { await expect(page.getByText(text, { exact: false }).first()).toHaveCount(0); }
async function upload(page, target, filePath) {
  let loc;
  if (/^(file input|file|upload|attachment)$/i.test(target.trim())) {
    loc = page.locator('input[type="file"]').first();
  } else {
    loc = (await resolve(page, target)).first();
  }
  await loc.setInputFiles(filePath);
}
async function assert_field_value(page, target, value) {
  await expect((await resolve(page, target)).first()).toHaveValue(value);
}
async function assert_file_state(page, target, wantAttached) {
  const n = await (await resolve(page, target)).first().evaluate(el => (el && el.files) ? el.files.length : 0);
  if (wantAttached && n === 0) throw new Error('expected a file to be attached to <' + target + '>, found none');
  if (!wantAttached && n > 0) throw new Error('expected no file attached to <' + target + '>, found ' + n);
}
async function assert_url_contains(page, fragment) { await expect(page).toHaveURL(new RegExp(escapeRegex(fragment))); }
async function screenshot(page, path) { await page.screenshot({ path: path, fullPage: true }); }

module.exports = {
  resolve, open_page, click, fill, select_option, check, uncheck, clear,
  hover, press_key, press, wait_for, assert_visible, assert_not_visible,
  assert_text_visible, assert_text_not_visible, assert_url_contains,
  upload, assert_field_value, assert_file_state, screenshot,
};
'''

_SPEC_HEADER = '''// Suite: {suite} — generated by qax spec_generator.
// Hand-edit sparingly; `qax heal` may patch this file after app updates.
const {{ test, expect }} = require('@playwright/test');
const h = require('./helpers');

'''


def _slug(text: str) -> str:
    return re.sub(r"\W+", "_", text.strip()).strip("_").lower() or "item"


def _clean_q(v: str) -> str:
    return v.strip().strip('"').strip("'").strip()


def compile_step(step: str, case_id: str) -> list[str]:
    """Compile one natural-language step into JS lines.

    Unsupported steps degrade to a ``// TODO(manual)`` comment so the healer
    agent can complete them.
    """
    s = step.strip()
    m = None
    if (m := re.match(r"^(?:open|go to|navigate to|visit|launch)\s+(.+)$", s, re.I)):
        return [f'    await h.open_page(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^click\s+(?:on\s+)?(.+?)\s+(\d+)\s+times?$", s, re.I)):
        target, n = _clean_q(m.group(1)), int(m.group(2))
        if n > 1:
            return [
                f"    for (let i = 0; i < {n}; i++) {{",
                f'        await h.click(page, "{target}")',
                "    }",
            ]
        return [f'    await h.click(page, "{target}")']
    if (m := re.match(r"^click\s+(?:on\s+)?(.+)$", s, re.I)):
        return [f'    await h.click(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^(?:fill|enter|type|input|set)\s+(.+?)\s+(?:with|into|to|as)\s+(.+)$", s, re.I)):
        return [
            f'    await h.fill(page, "{_clean_q(m.group(1))}", "{_clean_q(m.group(2))}")'
        ]
    if (m := re.match(r"^select\s+(.+?)\s+from\s+(.+)$", s, re.I)):
        return [
            f'    await h.select_option(page, "{_clean_q(m.group(2))}", "{_clean_q(m.group(1))}")'
        ]
    if (m := re.match(r"^check\s+(.+)$", s, re.I)):
        return [f'    await h.check(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^uncheck\s+(.+)$", s, re.I)):
        return [f'    await h.uncheck(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^clear\s+(.+)$", s, re.I)):
        return [f'    await h.clear(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^hover\s+(?:over\s+)?(.+)$", s, re.I)):
        return [f'    await h.hover(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^press\s+(.+?)\s+on\s+(.+)$", s, re.I)):
        return [
            f'    await h.press_key(page, "{_clean_q(m.group(2))}", "{_clean_q(m.group(1))}")'
        ]
    if (m := re.match(r"^press\s+(.+)$", s, re.I)):
        return [f'    await h.press(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^wait\s+for\s+(.+)$", s, re.I)):
        return [f'    await h.wait_for(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(
        r"^(?:expect|verify|assert|check that)\s+text\s+(.+?)\s+(?:is|to be|should be)\s+"
        r"(?:visible|displayed|shown|present)$",
        s, re.I,
    )):
        return [f'    await h.assert_text_visible(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(
        r"^(?:expect|verify|assert|check that)\s+text\s+(.+?)\s+(?:is|to be|should be)\s+"
        r"(?:not visible|hidden|absent|not displayed|not shown|not present)$",
        s, re.I,
    )):
        return [f'    await h.assert_text_not_visible(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(
        r"^(?:expect|verify|assert|check that)\s+(.+?)\s+(?:is|to be|should be|appears?)\s+"
        r"(?:visible|displayed|shown|present)$",
        s, re.I,
    )):
        return [f'    await h.assert_visible(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(
        r"^(?:expect|verify|assert|check that)\s+(.+?)\s+(?:is|to be|should be)\s+"
        r"(?:not visible|hidden|absent|not displayed|not shown|not present)$",
        s, re.I,
    )):
        return [f'    await h.assert_not_visible(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^(?:expect|verify|assert|check that)\s+text\s+(.+?)\s+(?:is|to be)\s+not\s+visible$", s, re.I)):
        # handled above (text rules run before generic not-visible)
        pass
    if (m := re.match(r"^upload\s+(.+?)\s+(?:to|into|on)\s+(.+)$", s, re.I)):
        return [
            f'    await h.upload(page, "{_clean_q(m.group(2))}", "{_clean_q(m.group(1))}")'
        ]
    if (m := re.match(r"^expect\s+(?:field|input)\s+(.+?)\s+(?:has|equals|is)\s+value\s+(.+)$", s, re.I)):
        return [
            f'    await h.assert_field_value(page, "{_clean_q(m.group(1))}", "{_clean_q(m.group(2))}")'
        ]
    if (m := re.match(r"^expect\s+(.+?)\s+has\s+no\s+file\s+attached$", s, re.I)):
        return [f'    await h.assert_file_state(page, "{_clean_q(m.group(1))}", false)']
    if (m := re.match(r"^expect\s+(.+?)\s+has\s+(?:a\s+)?file\s+attached$", s, re.I)):
        return [f'    await h.assert_file_state(page, "{_clean_q(m.group(1))}", true)']
    if (m := re.match(
        r"^(?:expect|verify|assert)\s+(?:the\s+)?(?:page\s+)?url\s+"
        r"(?:contains|matches|has|equals|is)\s+(.+)$",
        s, re.I,
    )):
        return [f'    await h.assert_url_contains(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^(?:expect|verify|assert)\s+text\s+(.+)$", s, re.I)):
        return [f'    await h.assert_text_visible(page, "{_clean_q(m.group(1))}")']
    if (m := re.match(r"^(?:wait|sleep|pause)\s+(\d+)\s*(?:s|sec|seconds)?$", s, re.I)):
        return [f"    await page.waitForTimeout({int(m.group(1)) * 1000})"]
    if (m := re.match(r"^screenshot(?:\s+(.+))?$", s, re.I)):
        fname = _clean_q(m.group(1)) if m and m.group(1) else f"{case_id}.png"
        return [f'    await h.screenshot(page, "{fname}")']
    return [f"    // TODO(manual): {step}"]


def _suite_spec(cases: list[TestCase]) -> tuple[Path, str]:
    suite = cases[0].suite
    lines = [_SPEC_HEADER.format(suite=suite)]
    for case in cases:
        meta = f"{case.case_id} | {case.title} | severity={case.severity} priority={case.priority}"
        lines.append(f'test("{meta.replace(chr(34), chr(92) + chr(34))}", async ({{ page }}) => {{')
        if case.expected_result:
            lines.append(f"    // expected: {case.expected_result}")
        for step in case.steps:
            lines.extend(compile_step(step, case.case_id))
        lines.append("});")
        lines.append("")
    return Path(f"suite_{_slug(suite)}.spec.js"), "\n".join(lines)


def generate_specs(cases: list[TestCase], tests_dir: Path, force: bool = False) -> list[Path]:
    """Write helpers.js (once) + one spec file per suite into tests_dir.

    Returns the list of written spec paths.
    """
    tests_dir.mkdir(parents=True, exist_ok=True)
    helpers_path = tests_dir / "helpers.js"
    if not helpers_path.exists():
        helpers_path.write_text(HELPERS_SOURCE, encoding="utf-8")

    by_suite: dict[str, list[TestCase]] = {}
    for case in cases:
        by_suite.setdefault(case.suite, []).append(case)

    written: list[Path] = []
    for suite_cases in by_suite.values():
        fname, content = _suite_spec(suite_cases)
        target = tests_dir / fname
        if target.exists() and not force:
            continue
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written
