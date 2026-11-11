"""Vibe-audit suite: WCAG/design-consistency test cases for generated UI.

The audits run in the real browser (headed with ``--headed``) against the app
URL. Each audit case maps to a check in ``audits.js`` (written into
``automation/tests/`` beside ``helpers.js``); the spec file is built from a
fixed template (not the step grammar) because audits are fixed checks, not
natural-language steps.

Failures here are treated as REAL defects: ``qax heal`` skips this suite so an
agent can never "heal" an accessibility failure into silence.
"""

from __future__ import annotations

import re
from pathlib import Path

from qax.excel_parser import TestCase

SUITE = "Vibe Audit"
SPEC_FILENAME = "suite_vibe_audit.spec.js"
ENGINE_FILENAME = "audits.js"

# --------------------------------------------------------------------------- #
# Audit engine (JS) — written into automation/tests/audits.js
# --------------------------------------------------------------------------- #
AUDITS_SOURCE = r'''// qax-generated UI / vibe audit engine (WCAG 2.2 + design-consistency).
// Every audit returns an array of human-readable failure strings ([] = pass).
// Only this file, helpers.js and the specs may be edited by the healer.
const axe = require('axe-core');

function parseColor(c) {
  if (!c) return null;
  const m = String(c).match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const p = m[1].split(',').map(s => parseFloat(s.trim()));
  return { r: p[0] || 0, g: p[1] || 0, b: p[2] || 0, a: p.length > 3 ? p[3] : 1 };
}
function channel(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
function lum(c) { return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b); }
function ratio(a, b) {
  const la = lum(a), lb = lum(b);
  const hi = Math.max(la, lb), lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}
function blend(fg, bg) {
  const a = fg.a;
  return { r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a), a: 1 };
}

// ---------- page-side collectors (run inside the browser) ----------

const COLLECT = function () {
  const WHITE = { r: 255, g: 255, b: 255, a: 1 };
  function parseColor(c) {
    if (!c) return null;
    const m = String(c).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(s => parseFloat(s.trim()));
    return { r: p[0] || 0, g: p[1] || 0, b: p[2] || 0, a: p.length > 3 ? p[3] : 1 };
  }
  function blend(fg, bg) {
    const a = fg.a;
    return { r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a), a: 1 };
  }
  function channel(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  function lum(c) { return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b); }
  function ratio(a, b) {
    const la = lum(a), lb = lum(b);
    const hi = Math.max(la, lb), lo = Math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
  }
  function effectiveBackground(el) {
    const layers = [];
    let cur = el;
    while (cur && cur.nodeType === 1) {
      const c = parseColor(getComputedStyle(cur).backgroundColor);
      if (c) { layers.push(c); if (c.a >= 0.99) break; }
      cur = cur.parentElement;
    }
    let bg = WHITE;
    for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
    return bg;
  }
  function visible(el) {
    if (!el.getClientRects || !el.getClientRects().length) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0;
  }
  function hiddenFromA11y(el) {
    return !!el.closest('[aria-hidden="true"]');
  }
  function hasDirectText(el) {
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && (n.textContent || '').trim()) return true;
    }
    return false;
  }
  function desc(el) {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cls = Array.from(el.classList || []).slice(0, 2).join('.');
    if (cls) s += '.' + cls;
    const txt = (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 60);
    if (txt) s += ' "' + txt + '"';
    return s;
  }
  function cssColor(c) {
    return 'rgb(' + Math.round(c.r) + ',' + Math.round(c.g) + ',' + Math.round(c.b) + ')';
  }
  const out = { text: [], ui: [] };
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'PATH']);

  // --- text contrast (WCAG 1.4.3: 4.5:1 normal, 3:1 large) ---
  const all = Array.from(document.querySelectorAll('body *'));
  for (const el of all) {
    if (SKIP.has(el.tagName)) continue;
    if (!visible(el) || hiddenFromA11y(el)) continue;
    const cs = getComputedStyle(el);
    const hasText = hasDirectText(el) || (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');
    if (!hasText) continue;
    const fg = parseColor(cs.color);
    if (!fg) continue;
    const bg = effectiveBackground(el);
    const fs = parseFloat(cs.fontSize) || 16;
    const bold = (parseInt(cs.fontWeight) || 400) >= 700;
    const need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
    const r = ratio(fg, bg);
    if (r < need - 0.01) {
      out.text.push('text ' + cssColor(fg) + ' on ' + cssColor(bg) + ' = ' + r.toFixed(2) + ':1 (need ' + need + ':1)  <' + desc(el) + '>');
    }
  }

  // --- non-text / UI component contrast (WCAG 1.4.11: 3:1) ---
  // The visible boundary decides what to test: a component with a real
  // border is identified by that border; a borderless component is
  // identified by its fill. (Testing a white input fill against a white
  // card would be a false positive — its border is the boundary.)
  const controls = 'button, [role="button"], a[href], input, select, textarea, summary, [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])';
  for (const el of Array.from(document.querySelectorAll(controls))) {
    if (!visible(el) || hiddenFromA11y(el)) continue;
    const cs = getComputedStyle(el);
    const own = parseColor(cs.backgroundColor);
    const behind = effectiveBackground(el.parentElement);
    const borderVisible = cs.borderStyle !== 'none' && parseFloat(cs.borderTopWidth) > 0;
    if (borderVisible) {
      const bc = parseColor(cs.borderTopColor);
      if (bc && bc.a > 0.05) {
        const comp = blend(bc, behind);
        const r = ratio(comp, behind);
        if (r < 2.99) out.ui.push('control border ' + cssColor(comp) + ' on ' + cssColor(behind) + ' = ' + r.toFixed(2) + ':1 (need 3:1)  <' + desc(el) + '>');
      }
    } else if (own && own.a > 0.05) {
      const comp = blend(own, behind);
      const r = ratio(comp, behind);
      if (r < 2.99) out.ui.push('control bg ' + cssColor(comp) + ' on ' + cssColor(behind) + ' = ' + r.toFixed(2) + ':1 (need 3:1)  <' + desc(el) + '>');
    }
  }
  return out;
};

// ---------- node-side audits (each returns Promise<string[]>) ----------

// WCAG 2.x A/AA scan via axe-core (serious + critical only).
async function axeAudit(page) {
  await page.addScriptTag({ content: axe.source });
  const res = await page.evaluate(() => new Promise((resolve) => {
    axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
    }, (err, r) => resolve(err ? { err: String(err) } : r));
  }));
  if (res.err) return ['axe.run failed: ' + res.err];
  const viols = (res.violations || []).filter(v => v.impact === 'critical' || v.impact === 'serious');
  return viols.map(v => v.id + ' (' + v.impact + '): ' + v.help +
    ' — ' + (v.nodes || []).slice(0, 3).map(n => n.target.join(' ')).join(' | '));
}

// Text contrast (WCAG 1.4.3 AA) — text kind only.
async function contrastText(page) {
  const data = await page.evaluate(COLLECT);
  return data.text;
}

// Non-text/UI contrast (WCAG 1.4.11 AA).
async function contrastUi(page) {
  const data = await page.evaluate(COLLECT);
  return data.ui;
}

// Heading order: no skipped levels, single h1.
async function headingOrder(page) {
  return page.evaluate(() => {
    const out = [];
    const hs = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
      .filter(h => h.getClientRects().length);
    if (!hs.length) return out;
    const first = parseInt(hs[0].tagName[1], 10);
    if (first !== 1) out.push('page starts at <h' + first + '> — first heading should be <h1>: <' + (hs[0].innerText || '').trim().slice(0, 60) + '>');
    let last = first;
    const h1s = hs.filter(h => h.tagName === 'H1').length;
    if (h1s > 1) out.push(h1s + ' <h1> headings on one page — use one h1, demote the rest');
    for (const h of hs.slice(1)) {
      const lvl = parseInt(h.tagName[1], 10);
      if (lvl > last + 1) {
        out.push('<h' + last + '> -> <h' + lvl + '> level skipped before "' + (h.innerText || '').trim().slice(0, 60) + '"');
      }
      last = lvl;
    }
    return out;
  });
}

// Touch targets: interactive controls >= 24x24 CSS px (WCAG 2.5.8 AA).
async function touchTargets(page) {
  return page.evaluate(() => {
    const out = [];
    const sel = 'button, [role="button"], input, select, textarea, summary, [role="checkbox"], [role="radio"], [role="switch"], [tabindex]:not([tabindex="-1"])';
    for (const el of Array.from(document.querySelectorAll(sel))) {
      if (el.getClientRects && !el.getClientRects().length) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const rect = el.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) continue;
      if (rect.width < 24 || rect.height < 24) {
        let s = el.tagName.toLowerCase();
        if (el.id) s += '#' + el.id;
        const txt = (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40);
        if (txt) s += ' "' + txt + '"';
        out.push(s + ' is ' + Math.round(rect.width) + 'x' + Math.round(rect.height) + 'px (min 24x24)');
      }
    }
    return out;
  });
}

// Icon-only buttons/links whose entire accessible text is symbols/emoji with
// no aria-label — invisible to screen readers (axe covers this as
// button-name; this adds an explicit emoji check).
async function emojiIcons(page) {
  return page.evaluate(() => {
    const out = [];
    const sel = 'button, a[href], [role="button"], [role="link"]';
    for (const el of Array.from(document.querySelectorAll(sel))) {
      if (el.getClientRects && !el.getClientRects().length) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.getAttribute('title')) continue;
      const txt = (el.innerText || '').replace(/\s+/g, '').replace(/[\uFE0F\u200D]/g, '');
      if (!txt) continue;
      if (/^[\p{So}\p{Sk}]+$/u.test(txt)) {
        let s = el.tagName.toLowerCase();
        if (el.id) s += '#' + el.id;
        out.push(s + ' has only symbol/emoji text "' + txt.slice(0, 8) + '" and no aria-label');
      }
    }
    return out;
  });
}

// Keyboard focus visibility: tab through the page and require a visible focus
// indicator (outline / box-shadow / background / border change).
async function focusVisible(page, maxTabs) {
  maxTabs = maxTabs || 12;
  const before = await page.evaluate(() => {
    const sel = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [tabindex]:not([tabindex="-1"])';
    const els = Array.from(document.querySelectorAll(sel))
      .filter(e => e.getClientRects && e.getClientRects().length &&
        getComputedStyle(e).visibility !== 'hidden');
    return els.slice(0, 60).map(e => {
      const cs = getComputedStyle(e);
      return { tag: e.tagName + (e.id ? '#' + e.id : ''), t: (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 30), outline: cs.outlineStyle + ' ' + cs.outlineWidth, shadow: cs.boxShadow, bg: cs.backgroundColor, border: cs.borderColor };
    });
  });
  const fails = [];
  for (let i = 0; i < Math.min(maxTabs, before.length); i++) {
    await page.keyboard.press('Tab');
    const state = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const cs = getComputedStyle(el);
      return { tag: el.tagName + (el.id ? '#' + el.id : ''), outline: cs.outlineStyle + ' ' + cs.outlineWidth, shadow: cs.boxShadow, bg: cs.backgroundColor, border: cs.borderColor };
    });
    if (!state) {
      // Focus moved to the browser chrome = end of the page's tab order.
      // Normal — stop. Only note when some collected elements were never
      // reachable (they are off-screen, inside a modal, or inert).
      if (i + 1 < before.length) {
        fails.push('only ' + (i + 1) + ' of ' + before.length + ' focusable elements were reachable by Tab (rest may be off-screen / modal / inert)');
      }
      break;
    }
    const base = before[i] || {};
    const outlineVisible = state.outline && state.outline.indexOf('none') === -1 && parseFloat(state.outline.split(' ')[1]) > 0;
    const changed = state.outline !== base.outline || state.shadow !== base.shadow || state.bg !== base.bg || state.border !== base.border;
    if (!outlineVisible && !changed) {
      fails.push('no visible focus indicator on <' + state.tag + '> "' + (base.t || '') + '" (outline/shadow/background unchanged on focus)');
    }
  }
  return fails;
}

// prefers-reduced-motion: with reduced motion emulated, infinite CSS
// animations still running are flagged (site does not honour the preference).
async function reducedMotion(page) {
  return page.evaluate(() => {
    const out = [];
    for (const a of document.getAnimations()) {
      const eff = a.effect;
      if (!eff || !eff.getTiming) continue;
      const t = eff.getTiming();
      if (t.iterations === Infinity && a.playState === 'running') {
        const name = (typeof a.animationName === 'string') ? a.animationName : '?';
        const el = eff.target;
        let s = el ? (el.tagName || '').toLowerCase() : '?';
        if (el && el.id) s += '#' + el.id;
        out.push('infinite animation "' + name + '" still running on <' + s + '> with reduced motion preferred');
      }
    }
    return out;
  });
}

// No horizontal overflow at the current viewport (run under a mobile
// viewport in the spec via test.use).
async function mobileOverflow(page) {
  return page.evaluate(() => {
    const out = [];
    const vw = document.documentElement.clientWidth;
    const sw = document.documentElement.scrollWidth;
    if (sw > vw + 1) {
      out.push('page scrolls horizontally: viewport ' + vw + 'px, content ' + sw + 'px');
      const wide = Array.from(document.querySelectorAll('body *'))
        .filter(e => e.getClientRects && e.getClientRects().length)
        .map(e => { const r = e.getBoundingClientRect(); return { e, r }; })
        .filter(x => x.r.right > vw + 1 && x.r.left < vw)
        .slice(0, 8)
        .map(x => {
          let s = x.e.tagName.toLowerCase();
          if (x.e.id) s += '#' + x.e.id;
          return s + ' (right edge ' + Math.round(x.r.right) + 'px)';
        });
      if (wide.length) out.push('overflowing elements: ' + wide.join(', '));
    }
    return out;
  });
}

// Theme consistency census: distinct font families and distinct text colors.
// Fails only on extreme drift (a sane design token system stays small).
async function themeCensus(page) {
  return page.evaluate(() => {
    const fonts = new Map();
    const colors = new Map();
    for (const el of Array.from(document.querySelectorAll('body *'))) {
      if (el.getClientRects && !el.getClientRects().length) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      let hasText = false;
      for (const n of el.childNodes) {
        if (n.nodeType === 3 && (n.textContent || '').trim()) { hasText = true; break; }
      }
      if (!hasText) continue;
      const fam = (cs.fontFamily.split(',')[0] || '').replace(/["']/g, '').trim();
      if (fam) fonts.set(fam, (fonts.get(fam) || 0) + 1);
      const m = String(cs.color).match(/rgba?\(([^)]+)\)/);
      if (m) {
        const key = m[1].split(',').map(s => Math.round(parseFloat(s) / 8) * 8).join(',');
        colors.set(key, (colors.get(key) || 0) + 1);
      }
    }
    const out = [];
    const fontList = Array.from(fonts.entries()).sort((a, b) => b[1] - a[1]);
    if (fontList.length > 4) {
      out.push(fontList.length + ' distinct font families: ' + fontList.slice(0, 6).map(f => f[0] + ' (x' + f[1] + ')').join(', '));
    }
    if (colors.size > 40) {
      const top = Array.from(colors.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5).map(c => 'rgb(' + c[0] + ') x' + c[1]);
      out.push(colors.size + ' distinct text colors (design-token drift?): top ' + top.join(', '));
    }
    return out;
  });
}

module.exports = {
  axe: axeAudit, contrastText: contrastText, contrastUi: contrastUi,
  headingOrder: headingOrder, touchTargets: touchTargets,
  emojiIcons: emojiIcons, focusVisible: focusVisible,
  reducedMotion: reducedMotion, mobileOverflow: mobileOverflow,
  themeCensus: themeCensus,
};
'''

# --------------------------------------------------------------------------- #
# Audit case registry (metadata shown in results.json / reports)
# --------------------------------------------------------------------------- #
# check -> (id, title, expected_result, severity, priority)
AUDIT_CASES: list[dict] = [
    {
        "case_id": "AUD-001",
        "title": "axe-core WCAG 2.x A/AA scan (serious+critical violations)",
        "check": "axe",
        "expected": "No serious/critical axe violations (labels, names, alt, aria, contrast, region)",
        "severity": "high", "priority": "P1",
    },
    {
        "case_id": "AUD-002",
        "title": "Text contrast WCAG 1.4.3 AA (4.5:1 normal / 3:1 large)",
        "check": "contrastText",
        "expected": "Every visible text element meets its contrast ratio against its real background",
        "severity": "high", "priority": "P1",
    },
    {
        "case_id": "AUD-003",
        "title": "UI component contrast WCAG 1.4.11 AA (3:1 buttons, borders, inputs)",
        "check": "contrastUi",
        "expected": "Buttons, borders and form controls meet 3:1 against the background behind them",
        "severity": "medium", "priority": "P1",
    },
    {
        "case_id": "AUD-004",
        "title": "Heading order (no skipped levels, single h1)",
        "check": "headingOrder",
        "expected": "Page starts at h1 and heading levels never skip (h1->h3 etc.)",
        "severity": "medium", "priority": "P2",
    },
    {
        "case_id": "AUD-005",
        "title": "Keyboard focus visibility (WCAG 2.4.7)",
        "check": "focusVisible",
        "expected": "Tab order shows a visible focus indicator on every interactive element",
        "severity": "high", "priority": "P1",
    },
    {
        "case_id": "AUD-006",
        "title": "Touch target size >= 24x24px (WCAG 2.5.8 AA)",
        "check": "touchTargets",
        "expected": "All interactive controls meet the 24x24px minimum target size",
        "severity": "medium", "priority": "P2",
    },
    {
        "case_id": "AUD-007",
        "title": "No emoji-only icon buttons without accessible names",
        "check": "emojiIcons",
        "expected": "Every icon button has an aria-label or real text — not emoji alone",
        "severity": "medium", "priority": "P2",
    },
    {
        "case_id": "AUD-008",
        "title": "prefers-reduced-motion respected (no infinite animations)",
        "check": "reducedMotion",
        "expected": "With reduced motion emulated, no infinite CSS animation keeps running",
        "severity": "low", "priority": "P3",
    },
    {
        "case_id": "AUD-009",
        "title": "Theme consistency census (fonts / text-color drift)",
        "check": "themeCensus",
        "expected": "Small set of font families and text colors (design tokens, not per-component hex)",
        "severity": "low", "priority": "P3",
    },
    {
        "case_id": "AUD-010",
        "title": "No horizontal overflow at 390px mobile viewport",
        "check": "mobileOverflow",
        "expected": "Page does not scroll horizontally on a 390px-wide viewport",
        "severity": "medium", "priority": "P2",
    },
]


def audit_test_cases() -> list[TestCase]:
    """TestCase objects (no steps — the spec template drives execution)."""
    return [
        TestCase(
            case_id=c["case_id"], suite=SUITE, title=c["title"],
            steps=[], expected_result=c["expected"],
            severity=c["severity"], priority=c["priority"],
        )
        for c in AUDIT_CASES
    ]


def _js_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# --------------------------------------------------------------------------- #
# Spec generation (fixed template, one test per audit case)
# --------------------------------------------------------------------------- #
def build_audit_spec(app_url: str) -> str:
    lines = [
        "// Suite: " + SUITE + " — generated by qax audit_suite.",
        "// Fix the APP, not this file: audit failures are real defects.",
        "const { test, expect } = require('@playwright/test');",
        "const a = require('./audits');",
        "",
        "// Whole suite emulates prefers-reduced-motion for AUD-008.",
        "test.use({ reducedMotion: 'reduce' });",
        "",
        "const APP_URL = " + _js_str(app_url) + ";",
        "",
    ]
    for c in AUDIT_CASES:
        check = c["check"]
        meta = f"{c['case_id']} | {c['title']} | severity={c['severity']} priority={c['priority']}"
        body_lines = {
            "axe": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.axe(page);\n"
                "  if (fails.length) throw new Error('axe serious/critical violations: ' + fails.length + '\\n' + fails.slice(0, 12).join('\\n'));"
            ),
            "contrastText": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.contrastText(page);\n"
                "  if (fails.length) throw new Error('text contrast failures: ' + fails.length + '\\n' + fails.slice(0, 12).join('\\n'));"
            ),
            "contrastUi": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.contrastUi(page);\n"
                "  if (fails.length) throw new Error('UI contrast failures: ' + fails.length + '\\n' + fails.slice(0, 12).join('\\n'));"
            ),
            "headingOrder": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.headingOrder(page);\n"
                "  if (fails.length) throw new Error('heading-order violations:\\n' + fails.join('\\n'));"
            ),
            "focusVisible": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.focusVisible(page, 12);\n"
                "  if (fails.length) throw new Error('focus-visibility violations (verify manually — heuristic):\\n' + fails.slice(0, 8).join('\\n'));"
            ),
            "touchTargets": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.touchTargets(page);\n"
                "  if (fails.length) throw new Error('undersized touch targets:\\n' + fails.slice(0, 10).join('\\n'));"
            ),
            "emojiIcons": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.emojiIcons(page);\n"
                "  if (fails.length) throw new Error('emoji-only interactive elements without aria-label:\\n' + fails.slice(0, 10).join('\\n'));"
            ),
            "reducedMotion": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.reducedMotion(page);\n"
                "  if (fails.length) throw new Error('infinite animations ignore reduced motion (verify manually):\\n' + fails.slice(0, 10).join('\\n'));"
            ),
            "themeCensus": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.themeCensus(page);\n"
                "  if (fails.length) throw new Error('theme drift (verify manually):\\n' + fails.join('\\n'));"
            ),
            "mobileOverflow": (
                "  await page.goto(APP_URL, { waitUntil: 'load' });\n"
                "  await page.evaluate(() => document.fonts.ready);\n"
                "  const fails = await a.mobileOverflow(page);\n"
                "  if (fails.length) throw new Error('mobile overflow:\\n' + fails.slice(0, 10).join('\\n'));"
            ),
        }[check]
        lines.append(f'test({_js_str(meta)}, async ({{ page }}) => {{')
        if check == "mobileOverflow":
            # Needs a phone-sized viewport: Playwright cannot change viewport
            # mid-test, so this case gets its own describe block.
            lines = lines[:-1]
            lines.append('test.describe("mobile viewport", () => {')
            lines.append("  test.use({ viewport: { width: 390, height: 844 } });")
            lines.append(f'  test({_js_str(meta)}, async ({{ page }}) => {{')
            indent = "  "
            for bl in body_lines.splitlines():
                lines.append(indent + bl if bl.strip() else "")
            lines.append("  });")
            lines.append("});")
        else:
            for bl in body_lines.splitlines():
                lines.append(bl if bl.strip() else "")
            lines.append("});")
        lines.append("")
    return "\n".join(lines)


def write_audit_files(app_url: str, tests_dir: Path, force: bool = False) -> list[Path]:
    """Write audits.js (when missing/changed) + the audit spec. Returns
    written paths."""
    tests_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    engine = tests_dir / ENGINE_FILENAME
    if not engine.exists() or engine.read_text(encoding="utf-8") != AUDITS_SOURCE:
        engine.write_text(AUDITS_SOURCE, encoding="utf-8")
        written.append(engine)
    spec = tests_dir / SPEC_FILENAME
    content = build_audit_spec(app_url)
    if force or not spec.exists() or spec.read_text(encoding="utf-8") != content:
        spec.write_text(content, encoding="utf-8")
        written.append(spec)
    return written


def is_audit_case(case: TestCase) -> bool:
    return case.suite == SUITE


def slugify_case_id(case_id: str) -> str:
    return re.sub(r"\W+", "_", case_id.strip()).strip("_").lower() or "item"
