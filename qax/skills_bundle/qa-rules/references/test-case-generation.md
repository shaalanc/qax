# Requirements-to-Test-Case Generation

Use this reference whenever the operator asks to create test cases, test scenarios, a test plan, a regression suite, or coverage from requirements, user stories, acceptance criteria, designs, API contracts, schemas, tickets, or code.

## Generation objective

Produce a **traceable, executable, risk-based test suite**, not a list of generic checks. Every requirement must map to one or more test cases, and every critical test case must identify its requirement, risk, actor, state, data, expected oracle, and evidence.

Do not claim that “all possible cases” can be enumerated literally. Instead, generate complete coverage across the applicable dimensions and explicitly record assumptions, exclusions, combinatorial reductions, and residual risk.

## Step 1: Normalize the source requirements

Extract and label:

| Element | Questions |
|---|---|
| Actors | Who can perform the action? Anonymous, user, admin, service, support, tenant owner? |
| Objects | What resources, records, files, payments, messages, or settings are affected? |
| Preconditions | Account state, role, tenant, feature flag, inventory, provider, or prior workflow? |
| Trigger | UI action, API call, import, webhook, queue event, schedule, retry, or deep link? |
| Happy path | What must happen when all inputs and dependencies are valid? |
| Rules | Required fields, calculations, authorization, uniqueness, limits, and state transitions? |
| Outcomes | UI, API, database, event, notification, audit, export, and external side effects? |
| Errors | What must happen for invalid input, conflict, timeout, dependency failure, or denial? |
| Non-functional needs | Performance, accessibility, security, privacy, compatibility, reliability, recovery? |
| Ambiguity | Which statements require clarification rather than assumption? |

Create a requirement traceability matrix before writing detailed cases.

## Step 2: Generate the mandatory test dimensions

For each behavior, generate applicable cases across this matrix:

| Dimension | Required variations |
|---|---|
| Functional | Valid minimum flow, valid typical flow, valid maximum/complex flow |
| Input validation | Missing, null, empty, whitespace, wrong type, malformed, unsupported enum, duplicate, injection-safe content |
| Boundaries | Below minimum, minimum, just above minimum, normal, just below maximum, maximum, above maximum, zero, negative, overflow |
| Actors | Anonymous, authenticated, verified, unverified, suspended, each role, downgraded role, support/service account |
| Scope | Same user, same tenant, another user, another tenant, deleted/archived object, restricted object |
| State | Initial, draft, pending, active, completed, cancelled, expired, archived, deleted, restored, conflicting/stale |
| Time | Before/at/after deadline, timezone, DST, leap day, date-only, clock skew, long-running operation |
| Repetition | First use, duplicate submit, retry, replay, refresh, back button, repeated update, repeated webhook |
| Concurrency | Two tabs, two users, simultaneous inventory/quota/payment, update conflict, out-of-order event |
| Dependency | Success, timeout, slow response, 4xx, 5xx, malformed response, partial success, unavailable provider |
| Data volume | Empty, one, page size, page boundaries, huge list, large file, many tenants, long history |
| UI/platform | Keyboard, screen reader, zoom, responsive layout, browser, OS, mobile lifecycle, offline/resume |
| Security/trust | Direct API call, altered IDs, hidden values, expired token, forged callback, cache after logout |
| Recovery | Refresh, crash, reconnect, migration, rollback, retry, restore, partial commit, reprocessing |
| Observability | User message, log, audit event, metric, alert, correlation ID, secret redaction |

Do not blindly create every Cartesian combination. Use pairwise or risk-based combination for low-risk dimensions, but fully cross high-risk dimensions such as actor × object scope, state × side effect, and timeout × retry.

## Step 3: Derive test cases from each requirement type

| Requirement type | Test-case families |
|---|---|
| Form/input | Valid, required, type, length, boundary, normalization, locale, error recovery, duplicate submit |
| Calculation | Representative values, rounding, precision, zero/negative, large values, independent oracle, reconciliation |
| CRUD/resource | Create, read, update, delete, restore, duplicate, stale version, linked records, authorization, audit |
| Workflow/state | Every allowed transition, every important forbidden transition, expiry, cancellation, approval separation, replay |
| Search/list/report | Empty, exact, partial, case, Unicode, special characters, sorting, pagination, filters, scope, export |
| Authentication | Login, failure, lockout, reset, expiry, refresh, logout, MFA, recovery, concurrent devices |
| Authorization | Horizontal, vertical, tenant isolation, stale role, direct API, deep link, export/download, background job |
| Payment/order | Price authority, tax, stock race, idempotency, timeout, duplicate webhook, refund, reconciliation |
| File/import | Extension/content mismatch, size, malformed file, encoding, duplicates, partial failure, rollback, retention |
| Notification | Opt-in/out, template data, localization, duplicate, delayed event, unsubscribe, privacy in preview |
| Integration | Contract schema, auth, timeout, retry, rate limit, malformed provider response, event order, reconciliation |
| Batch/job | Empty batch, mixed validity, retry, duplicate job, poison item, cancellation, progress, resume, dead letter |
| Mobile/offline | Permission, deep link, cold start, kill/resume, rotation, offline edit, conflict, low storage, old API |
| Accessibility | Keyboard order, focus, labels, errors, screen reader, contrast, zoom, motion, touch targets |
| Non-functional | Response time, throughput, concurrency, reliability, recovery, compatibility, privacy, auditability |

## Step 4: Write executable test cases

Use this schema for every detailed case:

```markdown
### TC-[area]-[number]: [behavior under test]

- **Requirement:** REQ-[ID]
- **Type:** Functional | Negative | Boundary | Security | Concurrency | Recovery | Accessibility | Compatibility | Performance | Integration
- **Priority:** P0 | P1 | P2 | P3
- **Automation:** Unit | Property | API | Contract | Integration | E2E | Manual exploratory
- **Actors/scope:** [role, user, tenant, object scope]
- **Preconditions:** [environment, flags, records, provider state, clock]
- **Test data:** [exact values, including boundary values]
- **Steps:**
  1. ...
  2. ...
  3. ...
- **Expected result:** [UI/API response, data invariant, side effects, audit/log behavior]
- **Evidence:** [response, screenshot, database/event/provider comparison]
- **Related cases:** [IDs for variants or regression]
```

Expected results must be observable and precise. “Works correctly” is not an oracle. Specify status, message, field behavior, state, records, side effects, permissions, timing, and recovery.

## Step 5: Check completeness

Before delivering the suite, perform these checks:

| Check | Pass condition |
|---|---|
| Traceability | Every requirement has at least one case; critical requirements have negative/boundary cases |
| Acceptance criteria | Each criterion is directly verified and linked to cases |
| Roles/scope | Every relevant actor and tenant boundary is covered |
| State | Allowed and important forbidden transitions are covered |
| Side effects | Duplicate, retry, timeout, partial failure, and reconciliation are covered |
| Data | Null, empty, boundaries, precision, Unicode, large values, and realistic records are covered |
| Security | Server-side authorization, direct API, sensitive data, and session lifecycle are covered |
| Integration | Critical dependencies have success, timeout, malformed, rate-limit, and outage cases |
| Non-functional | Applicable accessibility, compatibility, performance, reliability, privacy, and observability cases exist |
| Oracle quality | Expected results are independent, measurable, and not copied from implementation |
| Regression | Every confirmed defect has a permanent regression case |
| Gaps | Blocked, ambiguous, excluded, and untested areas are explicitly listed |

## Output modes

When the user supplies requirements, choose the most useful output:

- **Scenario inventory:** concise cases for early planning.
- **Detailed test cases:** fully executable cases using the schema above.
- **Traceability matrix:** requirement-to-case mapping with coverage status.
- **Regression pack:** prioritized cases for an existing feature or defect fix.
- **Automation backlog:** cases grouped by unit/API/integration/E2E/manual suitability.
- **Gap analysis:** missing requirements, ambiguous rules, untestable acceptance criteria, and residual risks.

If requirements are incomplete, generate cases from explicit requirements first, mark assumptions, and add clarification questions. Do not silently invent business rules.

## Special rule for AI-assisted code

When the feature was generated or modified by AI, add cases for implementation seams: duplicated code paths, server/client validation mismatch, mocked integrations, incorrect library defaults, hidden state, stale cache, async ordering, error rollback, authorization at the API boundary, and unit tests with weak or tautological oracles.
