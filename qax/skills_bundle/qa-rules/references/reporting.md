# Defect Evidence and Reporting

## Defect validation gate

```text
REPRODUCE → MINIMIZE → COMPARE WITH ORACLE → PROVE IMPACT → CHECK SCOPE →
CAPTURE EVIDENCE → CHECK DUPLICATES → IDENTIFY REGRESSION TEST → REPORT
```

Do not label an ambiguous requirement, environment issue, or unverified suspicion as a confirmed defect. Use `question`, `observation`, `risk`, or `blocked` when certainty is not established.

## Defect template

```markdown
# [ID] [Concise defect title]

## Summary
[One paragraph describing the user/business impact.]

## Environment
- Build/commit:
- Environment:
- Browser/device/API version:
- Account/role/tenant:
- Test data:

## Preconditions
1. ...

## Steps to reproduce
1. ...
2. ...
3. ...

## Expected result
[Requirement or invariant.] 

## Actual result
[Observed behavior, including whether data or side effects changed.]

## Evidence
[Logs, request/response, screenshots, database comparison, event ID, provider reference. Redact secrets and unnecessary personal data.]

## Impact and severity
[Explain reachability, affected data, business consequence, and rationale for P0–P3.]

## Scope and frequency
[Builds, roles, tenants, platforms, reproducibility rate, and whether systemic.]

## Workaround
[Only if verified.]

## Suggested regression test
[Stable automated or manual test case.] 

## Retest result
[Build, date, tester, result, evidence, and remaining risk.]
```

## Severity guidance

| Severity | Meaning |
|---|---|
| P0 | Catastrophic compromise, destructive loss, unsafe critical action, or uncontrolled financial exposure |
| P1 | Core workflow, sensitive data, authorization, payment/order integrity, or major recovery failure |
| P2 | Important edge case, accessibility, compatibility, operational, or intermittent failure |
| P3 | Cosmetic or low-impact issue |

Severity is based on impact and exploitability/reachability, not on how easy the bug is to reproduce.

## Quality summary template

Report tested build and scope, environments and accounts, executed cases, pass/fail/blocked counts, critical defects, fixed-defect retests, flaky tests, untested areas, known limitations, and residual risk. State clearly whether the recommendation is `go`, `go with accepted risk`, or `no-go`, and connect that recommendation to evidence rather than intuition.
