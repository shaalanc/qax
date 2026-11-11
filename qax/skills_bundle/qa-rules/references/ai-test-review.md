# AI-Assisted Code and Test Review

Use this reference whenever code, tests, fixtures, documentation, or configuration has been generated or materially modified by an AI coding assistant.

## Review stance

Treat generated code as a plausible draft, not as evidence of correctness. Review the requirement, the invariant, the boundary, and the integration behavior independently from the implementation.

## Common generated-test failure patterns

| ID | Smell | Detection | Required counter-test |
|---|---|---|---|
| T-01 | Happy-path-only suite | Almost all fixtures are valid and one-role | Add missing, null, boundary, unauthorized, duplicate, stale, and interrupted cases |
| T-02 | Implementation-coupled assertions | Tests focus on private methods, mocks, call counts, or exact query shape | Assert external behavior and domain invariants |
| T-03 | Excessive mocking | Auth, DB, queue, clock, provider, serializer, and network all mocked | Add contract, component, integration, and provider-sandbox tests |
| T-04 | Clean fixtures | One tenant, short strings, no legacy/null/duplicate records | Add production-shaped anonymized and adversarial data |
| T-05 | Tautological oracle | Expected result uses the same helper/formula as production | Use independent examples, golden data, ledger comparison, or property assertions |
| T-06 | Weak exception tests | Assert only 400/500 or a thrown error | Verify rollback, no side effect, safe message, logs, alert, and retry |
| T-07 | Missing state tests | No illegal transition, stale form, cancellation, expiry, or restore case | Build and test a state-transition matrix |
| T-08 | Missing time control | Uses current time, local timezone, sleep, or scheduler race | Inject a clock and test before/at/after expiry, DST, and clock skew |
| T-09 | Async not awaited | Test completes before job/event/commit | Await durable completion and assert eventual state with bounded polling |
| T-10 | No concurrency testing | No parallel actors or duplicate requests | Add race, double-submit, optimistic-lock, and duplicate-event tests |
| T-11 | Coverage worship | High line coverage but weak branch, mutation, state, requirement, or risk coverage | Use mutation testing and risk-based coverage review |
| T-12 | Snapshot overuse | Huge snapshots updated without semantic review | Replace with targeted authorization, data, accessibility, and contract assertions |
| T-13 | Flaky retries | CI reruns hide nondeterminism | Diagnose order, cleanup, clock, race, network, and isolation causes |
| T-14 | Hallucinated APIs | Nonexistent options, deprecated calls, insecure defaults, wrong version behavior | Compile, pin versions, consult official docs, and add behavior contract tests |
| T-15 | Role-blind security tests | Every fixture is admin or same tenant | Build actor × resource × action matrix and assert denial boundaries |
| T-16 | Configuration blindness | Tests use permissive local defaults | Run production-like config, migrations, cookies, CORS, flags, and secrets checks |

## Review questions

1. What requirement or invariant does each test independently prove?
2. Which test would fail if a comparison changed from `<=` to `<`?
3. Which test proves that an unauthorized user cannot perform the operation through the API?
4. Which test proves idempotency after a timeout where the server committed but the client saw no response?
5. Which test proves rollback when the second collaborator fails?
6. Which test runs with a different timezone, locale, tenant, and role?
7. Which test detects a duplicate webhook, queue message, or job execution?
8. Which test verifies safe errors without leaking secrets and sufficient logs for diagnosis?
9. Which test uses a genuinely independent expected value?
10. Which critical integration is mocked but not covered by a contract or sandbox test?

## Required gates before approving generated tests

- Every critical requirement maps to at least one test and one negative or boundary test.
- Authorization and tenant isolation are verified at the server/API boundary.
- Side effects have idempotency, retry, and timeout coverage.
- State transitions include illegal, stale, cancelled, expired, and concurrent cases where applicable.
- At least one test uses an independent oracle or invariant.
- Mocks are justified; real integration behavior is covered at the appropriate layer.
- Time, locale, platform, and configuration assumptions are explicit.
- Flaky tests are diagnosed rather than hidden by retries.
- Mutation or equivalent fault-injection evidence supports the important rules.
- The suite can fail for a realistic regression, not only for a syntax or mock mismatch.
