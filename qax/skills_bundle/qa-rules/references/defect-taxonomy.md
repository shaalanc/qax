# QA Defect Taxonomy

Use this reference when planning or extending tests. Convert each applicable pattern into a concrete case with actor, preconditions, action, expected result, evidence, and priority.

## Functional and data defects

| ID | Pattern | High-yield probes |
|---|---|---|
| F-01 | Validation exists in UI but not server | Omit, null, empty, whitespace, wrong type, malformed JSON, direct API call |
| F-02 | Client/server validation mismatch | Submit identical values through browser, mobile, API, import, and background job |
| F-03 | Off-by-one boundary | Test min−1, min, min+1, max−1, max, max+1, zero, negative, and overflow |
| F-04 | Unicode/localization defect | Accents, emoji, RTL, combining characters, long text, locale-specific case and numbers |
| F-05 | Duplicate or replayed operation | Double click, refresh, timeout retry, same idempotency key, duplicated webhook |
| F-06 | Partial success misreported | Mixed-validity batch, interruption, retry failed items, inspect committed records |
| F-07 | Lost update | Two users edit different fields or the same record from stale versions |
| F-08 | Illegal state transition | Attempt every meaningful state pair, including stale and expired transitions |
| F-09 | Pagination/search/sort defect | Insert while paging, page boundaries, nulls, numeric sort, tenant-scoped search |
| F-10 | Error-state confusion | Empty, loading, 401, 403, 404, 409, 429, 500, offline, and timeout |
| F-11 | Retry/timeout side-effect defect | Drop response after commit; verify one payment, order, email, or job |
| F-12 | Race condition | Simultaneous inventory, quota, balance, uniqueness, reservation, or approval requests |
| F-13 | Time defect | UTC/local zones, DST, date-only values, leap day, expiry boundary, clock skew |
| F-14 | Precision/rounding defect | Currency, tax, percentages, negative values, conversions, repeated calculations |
| F-15 | File/data handling defect | Spoofed extension, malformed content, large file, interruption, unsafe name/path, orphan |
| F-16 | Background/event defect | Duplicate jobs, poison messages, out-of-order events, reconciliation, dead-letter behavior |
| F-17 | Cache/local-state defect | Stale price, role, entitlement, status, post-logout data, offline conflict |
| F-18 | Accessibility/platform defect | Keyboard, screen reader, focus, zoom, contrast, responsive layout, browser/device matrix |

## Security and trust-boundary defects

Test only within explicit authorization and use approved staging or synthetic data where possible.

| ID | Pattern | High-yield probes |
|---|---|---|
| S-01 | Broken object authorization | Change resource IDs between two accounts; test detail, update, delete, export, and download |
| S-02 | Broken function authorization | Invoke admin or privileged API as normal, suspended, expired, or downgraded role |
| S-03 | Tenant isolation failure | Compare list, search, aggregation, autocomplete, exports, notifications, cache, and jobs |
| S-04 | Authentication lifecycle failure | Expired tokens, refresh rotation, logout, password change, reset, MFA, recovery, lockout |
| S-05 | Server trusts client values | Alter hidden role, price, quantity, tenant, approval, discount, or feature flag fields |
| S-06 | Injection or unsafe rendering | Harmless probes in search, filters, templates, rich text, filenames, and imports |
| S-07 | Sensitive data exposure | Inspect responses, logs, errors, browser storage, URLs, exports, email, and push previews |
| S-08 | Configuration/dependency failure | Debug mode, default credentials, permissive CORS, source maps, vulnerable/unpinned packages |
| S-09 | Integrity/webhook failure | Alter signature, timestamp, event ID, body, replay old callback, deliver out of order |
| S-10 | Logging/alerting failure | Privileged change, failed auth, export, deletion, and payment; verify actor, target, outcome, alert |

## Domain probes

| Domain | Probe |
|---|---|
| Ecommerce | Price change after cart add, stock race, expired/stacked coupon, tax/currency, payment retry, partial refund |
| B2B SaaS | Tenant isolation, seats and quotas, downgrade, approval separation, import/export, integration rotation |
| Payments | Idempotency, provider timeout, duplicate webhook, delayed capture, partial refund, ledger reconciliation |
| Marketplace | Buyer/seller isolation, concurrent purchase, commissions, dispute/refund, moderation, blocked-user access |
| Booking | Slot race, hold expiry, timezone/DST, cancellation policy, stale price, payment after expiry |
| HR/CRM | PII visibility, restricted notes, duplicate import, assignment, retention purge, departed-user access |
| Healthcare/safety | Consent, identity, units, abnormal values, emergency override, immutable audit, offline sync |
| Content/social | Privacy/search/cache, blocked users, moderation edits, Unicode confusables, media deletion |
| Logistics | Address, duplicate/out-of-order scans, split shipment, return, label loss, carrier outage |
| Mobile | Permissions, deep links, push cold-start, kill/resume, rotation, offline sync, storage, old API |
| Reporting/admin | Scope, aggregation, timezone boundary, huge export, CSV safety, scheduled-report permissions |

## Mandatory matrix

For every critical feature, vary input, actor, tenant, state, time, concurrency, network, data volume, device/platform, recovery, and trust. A feature is not covered merely because one valid UI journey passes.
