# Production Analytics Design — CredResolve

## 1. Layered architecture

| Layer | Purpose | Controls / output |
|---|---|---|
| Raw | Immutable source snapshots | source file, ingestion timestamp, checksum, schema version |
| Staging | Type normalization, timestamp parsing, source-specific dedupe | row counts, rejected-row quarantine |
| Clean | Standardized keys and explicit null/invalid flags | source key uniqueness and referential checks |
| Golden | Governed entities and events | canonical payment IDs; account ID remains account grain |
| Feature | Time-windowed account features | point-in-time joins; no future leakage |
| Metrics | Versioned metric definitions | numerator, denominator, grain, window, exclusions |
| Dashboard | Executive decision view | freshness, coverage, confidence, alert status |

## 2. Primary keys and identity policy

| Entity/event | Candidate primary key | Current confidence / policy |
|---|---|---|
| Account | `account_id` | Unique in supplied account master; account grain |
| Borrower | `borrower_id` | Cross-source links conflict; preserve source-specific IDs |
| Payment | `payment_id` | Use after processor confirms immutability; quarantine conflicting groups |
| Call attempt | `attempt_id` | Unique in extract; do not join via `call_id` without account/time validation |
| Call | `call_id` | Duplicate and cross-source collisions observed |
| Disposition | `disposition_id` | Unique in extract; call linkage unreliable |
| SMS / WhatsApp event | event row ID | Message ID is not unique to one account |
| Field visit | `visit_id` | Unique in extract; outcome PAID is not payment evidence |
| PTP | `ptp_id` | No direct payment foreign key; do not assert kept from account-only match |
| Targeting | `target_id` | Validate uniqueness and campaign date relationship |
| Agent | composite identity unresolved | No single stable cross-source key; no agent productivity leaderboard |

Never overwrite source IDs with inferred identities. Maintain `source_system`, `source_record_id`, `canonical_id`, `match_method`, `match_confidence`, `valid_from`, `valid_to`, and `review_status` in governed crosswalk tables. Ambiguous matches remain unresolved.

## 3. Metric contracts

Every metric registry entry must specify: `metric_id`, name, business definition, grain, numerator, denominator, event-time window, timezone, inclusion/exclusion rules, source tables, owner, version, effective date, freshness SLA, and test query.

| Metric | Production definition | Current status |
|---|---|---|
| Gross recovery | Sum of unique successful positive payments by payment event date | Reconstructed for Jan–Aug; Aug partial |
| Recovery rate | Successful recovery / eligible opening balance for same cohort and period | Not calculable: historical denominator absent |
| Contact rate | Unique eligible accounts with verified two-way human contact / unique eligible accounts attempted | Not calculable: no governed contact/RPC code |
| RPC | Unique accounts with verified right-party contact / unique accounts attempted | Not calculable: disposition mapping ungoverned |
| PTP rate | Unique valid PTP accounts / unique verified RPC accounts | Not calculable: RPC unavailable |
| PTP kept | PTP promises paid in full/defined tolerance by due date / matured valid PTPs | Not calculable: no promise-to-payment key |
| Recovery per agent-hour | Attributed net recovery / productive, deduplicated agent hours | Not calculable: agent identity/session attribution unreliable |
| Cost per rupee | Fully loaded channel cost / attributable recovery | Not calculable: cost and attribution absent |
| Channel conversion | Randomized assigned accounts with qualifying outcome / all assigned eligible accounts | Must be measured in experiment, not observational event logs |

## 4. Incremental processing and late events

- Ingest append-only batches with `batch_id`, `source_file`, `ingested_at`, checksum, schema version and source watermark.
- Use event time for business windows and ingestion time for operational latency. Preserve original timestamp string and parsed UTC timestamp; retain source timezone and conversion rule.
- Reprocess a rolling 7-day event-time window plus all late-arriving records. Recompute affected account-day and month partitions.
- Use idempotent `MERGE`/upsert on validated event keys. Never silently drop key conflicts; write them to quarantine and alert.
- Backfills are versioned, parameterized by source and date range, run in shadow mode, reconciled to prior outputs, and promoted only after owner approval.
- Keep immutable snapshots and metric-definition versions so historical dashboards can be reproduced.

## 5. Data quality gates

| Check | Severity | Action |
|---|---|---|
| Payment ID has conflicting account, amount, status or event time | Critical | Quarantine group; block financial KPI publication |
| Successful payment amount <= 0 or missing account/event time | High | Quarantine / investigate |
| Account master duplicate account ID | Critical | Block account-grain metrics |
| Event borrower differs from account master borrower | High | Preserve both; exception register; no auto-correction |
| Campaign targeting outside start/end | High | Flag campaign attribution; exclude from campaign-effect claims |
| Call/message key maps to multiple accounts | High | Block cross-source join and conversion KPI |
| Timestamp parse failure / unknown timezone | High | Quarantine from hour-of-day analysis |
| Source freshness beyond SLA | High | Show stale badge; suppress current-period comparison |
| Monthly total changes beyond tolerance after backfill | High | Reconcile and publish restatement note |

## 6. Monitoring and anomaly detection

Monitor source freshness, row-count drift, schema drift, key uniqueness, null rates, referential integrity, duplicate/conflict rates, late-arrival distribution, event-to-ingestion lag, payment totals, account coverage, and month-over-month metric revisions. Use robust trailing median/MAD or control limits only after enough stable history exists; alert on both data anomalies and genuine operational movement. Every alert must include affected source, time range, expected/observed value, severity, owner and runbook.

## 7. Experiment design before ₹10 Cr scale-up

Randomize eligible accounts within DPD × balance band × risk segment × client strata to treatment and business-as-usual holdout. Assignment is sticky at account level; analyze intention-to-treat. Pre-register primary outcome as 30-day incremental net recovery per eligible assigned account, with 60-day maturity sensitivity. Deduct channel, servicing and incentive costs. Track complaints, opt-outs, contact pressure and rollbacks as guardrails. Calculate sample size from baseline variance and minimum economically meaningful lift before launch. No pilot lift is claimed from the current observational dataset.

## 8. Operational ownership

Data engineering owns ingestion, contracts, backfills and lineage; collections operations owns disposition semantics and campaign calendars; finance owns payment reconciliation and cost allocation; analytics owns metric registry and experiment analysis; risk/compliance owns contact-pressure and complaint guardrails. A metric cannot be promoted to executive status without a named owner and signed definition.
