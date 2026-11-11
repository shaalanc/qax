# Risk-Based QA Test Strategy

## 1. Establish scope

Record product, build/commit, environment, supported platforms, feature flags, roles, tenants, test data, external providers, known limitations, and explicit authorization for destructive or load activity.

## 2. Prioritize risk

Use impact × likelihood × reachability × change risk. Start with:

| Priority | Typical focus |
|---|---|
| P0 | Catastrophic data loss, privilege escalation, uncontrolled financial action, unsafe critical action |
| P1 | Core workflow failure, sensitive-data exposure, tenant leakage, payment/order corruption, broken recovery |
| P2 | Meaningful edge case, accessibility, compatibility, operational, or intermittent defect |
| P3 | Cosmetic or narrowly scoped low-impact issue |

## 3. Select test level

| Need | Prefer |
|---|---|
| Pure deterministic rule | Unit and property-based test |
| API schema and boundary | Contract/component test |
| Real database, queue, cache, or provider behavior | Integration/sandbox test |
| Critical user journey | End-to-end test |
| Unknown risks and workflow gaps | Time-boxed exploratory session |
| Reliability and race behavior | Fault injection, concurrency, resilience, or controlled load test |
| UI semantics | Accessibility and cross-browser/device test |

## 4. Coverage ledger

Maintain a ledger with one row per meaningful combination of feature, actor, resource, state, risk class, environment, and result.

```text
feature | actor/role | tenant | state | risk class | environment | test/case | status | evidence | next lead
```

Allowed statuses are `tested-pass`, `tested-fail`, `blocked`, `not-applicable`, and `untested`. Never use “covered” without a case ID and evidence.

## 5. Exploratory session charter

Define a mission, not a random tour:

```text
Mission: discover defects in [feature] around [risk]
Actors/data: [roles, tenants, records]
Heuristics: boundary, state, concurrency, retry, time, trust, accessibility
Time box: [duration]
Stop condition: [evidence or coverage target]
Output: defects, observations, tested areas, open leads, residual risk
```

## 6. Release gate

For critical features, require server-side validation; actor/resource authorization; tenant isolation; state-transition coverage; idempotency and retry coverage for side effects; migration/rollback verification; production-like configuration; safe errors; audit/alert checks; accessibility on core journeys; and integration tests for critical external providers.

A green unit suite is not a release gate by itself.

## 7. When to pause and ask

Ask before modifying production data, running destructive actions, causing real notifications or paid provider calls, testing outside the approved security boundary, using real secrets/PII, or running load/fault tests that may affect availability. Proceed independently for local analysis, synthetic data, read-only inspection, test creation, and approved staging reproduction.
