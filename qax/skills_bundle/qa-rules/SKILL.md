---
name: qa-rules
description: >
  Use for ANY software quality-assurance task involving web apps, mobile apps, APIs,
  B2B SaaS, ecommerce, marketplaces, payments, data workflows, or AI-assisted code:
  test planning, exploratory testing, regression, negative and edge-case testing,
  API and UI verification, accessibility, compatibility, performance, reliability,
  test automation, unit-test review, defect validation, release readiness, or QA
  reporting. Activates automatically for QA and software-testing sessions. Uses an
  autonomous, risk-based, evidence-driven methodology that maps requirements and
  state transitions, probes happy paths and failure paths, tracks coverage to avoid
  blind spots, challenges weak test oracles, validates defects before reporting, and
  never claims quality from green unit tests alone. The operator may write in any
  language; keep technical artifacts in English unless asked otherwise.
---

# THE QUALITY ENGINE

**Your objective is not to produce activity. Your objective is to find meaningful defects, prove them reproducibly, and establish what has actually been tested.**

This skill is a framework for senior QA judgment, not a script. Apply it to the product, risk, data, and release context in front of you.

## Core operating principles

- **Test the product contract, not merely the implementation.** Derive expected behavior from requirements, domain rules, API contracts, UX rules, security policy, and invariants.
- **Map systems, not isolated screens.** Follow flows across UI, API, database, queues, webhooks, external providers, notifications, analytics, and exports.
- **Prioritize impact.** Start with authentication, authorization, tenant isolation, money, destructive actions, sensitive data, state transitions, integrations, and recovery.
- **Attack assumptions safely.** Exercise valid, invalid, boundary, stale, duplicated, concurrent, interrupted, localized, and unauthorized conditions in an authorized environment.
- **Treat every observation as a lead.** After each result, ask what it implies about validation, state, trust, data integrity, time, retries, and neighboring surfaces.
- **Never confuse coverage with correctness.** Passing tests and high line coverage do not prove that the oracle is independent, the mocks are realistic, or the business invariant is protected.
- **Never claim “secure,” “bug-free,” or “fully tested” without a bounded scope and explicit evidence.** Report what was tested, what was not tested, and the residual risk.
- **Protect data and scope.** Use synthetic or approved data, avoid destructive production actions unless explicitly authorized, and keep artifacts organized by project and environment.

## The reflex before every test action

```text
BEFORE EVERY MOVE:
  ✓ State the goal in one line and keep a visible plan.
  ✓ Confirm application, environment, account, tenant, role, and scope.
  ✓ Identify the expected oracle before executing the action.
  ✓ Ask whether this is a happy path, negative case, edge case, state, concurrency,
    recovery, compatibility, accessibility, performance, or trust-boundary probe.
  ✓ Prefer deterministic inspection or a focused test over blind repetition.
  ✓ Check the coverage ledger before repeating work.
  ✓ Save important observations immediately.
  ✓ Do not use real secrets or unnecessary personal data.
  ✓ If the operation changes data, requires production access, or may trigger cost,
    notifications, or irreversible side effects, obtain explicit approval first.
```

## The observation engine: I SEE → THEREFORE → I TEST

After every request, response, screen, log, test result, or defect symptom:

```text
I SEE:       status, payload, headers, UI state, timing, IDs, error, log, or data change
THEREFORE:   likely rule, assumption, state, trust boundary, dependency, or failure mode
I TEST:      3–5 focused follow-ups that could confirm or disprove the deduction
```

For example, if a UI hides an action for a normal user, test the endpoint directly; if a retry follows a timeout, test whether the side effect happened once or twice; if one tenant’s record appears in a search result, test list, export, autocomplete, cache, notification, and background-job paths.

## Requirements-to-test-case generation

When the operator provides requirements, user stories, acceptance criteria, designs, API contracts, schemas, tickets, or code and asks for test cases, make this the primary workflow:

1. Normalize the requirements into actors, objects, preconditions, triggers, happy paths, rules, outcomes, errors, non-functional needs, and ambiguities.
2. Build a requirement traceability matrix before writing detailed cases.
3. Generate applicable variants across input validation, boundaries, actors, tenant scope, state transitions, time, repetition, concurrency, dependencies, data volume, UI/platform, security/trust, recovery, and observability.
4. Derive domain-specific cases for forms, calculations, CRUD, workflows, search, authentication, authorization, payments, files, notifications, integrations, jobs, mobile/offline behavior, accessibility, and non-functional requirements.
5. Write executable cases with requirement ID, type, priority, automation level, actor/scope, preconditions, exact test data, steps, measurable expected results, evidence, and related cases.
6. Check completeness for traceability, acceptance criteria, roles, state, side effects, data, security, integrations, non-functional behavior, oracle quality, regression, and explicit gaps.
7. Do not silently invent business rules. Mark assumptions and ask clarification questions for ambiguous requirements while still generating cases for the explicit behavior.

Read `references/test-case-generation.md` for the full generation matrix, test-case schema, completeness checks, and output modes.

## Standard QA workflow

1. **Lock the goal and scope.** Identify the product, release, environment, supported platforms, roles, tenants, test data, and stop conditions.
2. **Reconnaissance and modeling.** Map actors, resources, workflows, state transitions, integrations, asynchronous jobs, data classifications, and crown-jewel operations.
3. **Risk prioritization.** Rank impact × likelihood × reachability × change risk. Begin with P0/P1 trust, integrity, money, privacy, and core workflows.
4. **Build the test matrix.** For every critical feature include valid, missing, null, malformed, boundary, duplicate, stale, concurrent, interrupted, unauthorized, localized, offline, and recovery variants.
5. **Execute in layers.** Use unit/property tests for pure rules; API/contract tests for boundaries; integration tests for real collaborators; end-to-end tests for critical journeys; exploratory testing for unknown unknowns.
6. **Record coverage continuously.** Log feature × actor × state × risk class × environment × result. Mark tested, blocked, not applicable, and untested.
7. **Validate defects.** Reproduce from a clean state, minimize the steps, compare with the intended oracle, assess impact, check for duplicates, and verify whether the issue is systemic.
8. **Report and retest.** Provide exact preconditions, steps, expected/actual results, evidence, severity rationale, affected versions, workaround, and regression results.
9. **Close with residual risk.** State remaining gaps, environmental limitations, flaky tests, untested integrations, and release recommendations.

## High-yield defect families

Always consider these families when relevant:

| Family | Probe for |
|---|---|
| Validation | Missing, null, empty, wrong type, Unicode, length, encoding, boundary, server/client mismatch |
| Authorization | Horizontal and vertical access, tenant isolation, stale role, direct API calls, export and search scope |
| Authentication | Expiry, refresh, logout, reset, MFA, recovery, lockout, session and device lifecycle |
| State | Illegal transitions, stale forms, duplicate actions, delete/restore, approval, cancellation, expiry |
| Integrity | Rounding, conservation, uniqueness, inventory, totals, ledger reconciliation, idempotency |
| Time | Timezones, date-only values, DST, leap day, expiry, clock skew, scheduling |
| Concurrency | Double submit, races, optimistic locking, duplicate webhook, out-of-order events |
| Resilience | Timeout, retry, partial failure, offline, crash, queue poison message, provider outage |
| Files/data | Content-type spoofing, size, path/name handling, import/export, orphan cleanup, retention |
| UI/platform | Keyboard, screen reader, zoom, responsive layouts, browser/device matrix, app lifecycle |
| Observability | Safe errors, audit trail, correlation IDs, metrics, alerts, secret redaction |
| Dependencies/config | Migrations, flags, CORS, cookies, headers, versions, build artifacts, secrets, default config |

Read `references/defect-taxonomy.md` for the detailed catalog, `references/ai-test-review.md` for AI-generated code and unit-test failure patterns, `references/test-strategy.md` for execution and coverage mechanics, and `references/reporting.md` for defect evidence and release reporting.

## AI-assisted development rules

Assume AI-generated code may be locally plausible but globally incomplete. Specifically inspect for:

- tests that mirror implementation rather than requirements;
- mocks that hide authorization, serialization, retry, transaction, or provider behavior;
- happy-path-only fixtures;
- missing null, boundary, concurrency, time, and recovery cases;
- copied formulas and non-independent test oracles;
- hallucinated library options, deprecated APIs, insecure defaults, or wrong version semantics;
- high line coverage with weak branch, mutation, state, requirement, or risk coverage;
- error tests that assert only a status code without rollback, side-effect, logging, or retry behavior;
- UI-only controls with no server-side enforcement;
- duplicated code paths whose behavior diverges across browser, mobile, API, import, and job interfaces.

Use `references/ai-test-review.md` before approving a generated test suite or declaring a feature sufficiently tested.

## Evidence and defect gate

Before reporting a defect, pass all applicable gates:

```text
REPRODUCE → MINIMIZE → COMPARE WITH ORACLE → PROVE IMPACT → CHECK SCOPE →
CAPTURE EVIDENCE → CHECK DUPLICATES → IDENTIFY REGRESSION TEST → REPORT
```

A suspected issue is not a confirmed defect when the requirement is ambiguous, the environment is misconfigured, the result is caused by test data, or the impact is inferred but not demonstrated. In those cases report it as a question, risk, observation, or blocked verification rather than overstating certainty.

## Safe autonomy boundaries

Proceed autonomously for read-only analysis, synthetic-data testing, local test execution, test design, log review, and defect reproduction in an approved environment. Ask before destructive writes, production data changes, mass notifications, paid provider actions, load tests that may affect availability, security tests outside an explicit authorization boundary, or handling real secrets and personal data.

## Language and output

Understand operator instructions in any language and mirror that language in conversation. Keep test cases, bug reports, API examples, code, and technical artifacts in English unless the operator requests another language. Use complete, evidence-based writing. Never hide uncertainty behind confident wording.

## Completion standard

Do not stop merely because the main flow works or the unit suite is green. Stop when the agreed scope and risk matrix are covered, remaining gaps are explicit, critical defects are validated or ruled out with evidence, and the final report states the tested build, environment, accounts, data, limitations, and residual risk.

## Bundled references

- `references/defect-taxonomy.md`: Cross-domain defect patterns and executable probes.
- `references/ai-test-review.md`: AI-generated code, unit-test, mocking, oracle, mutation, and coverage review guidance.
- `references/test-strategy.md`: Risk-based planning, coverage ledger, test-level selection, exploratory sessions, and release gates.
- `references/reporting.md`: Defect validation, severity, evidence, retest, and quality-summary templates.
- `references/test-case-generation.md`: Requirements-to-test-case workflow, coverage dimensions, detailed case schema, and completeness checks.
