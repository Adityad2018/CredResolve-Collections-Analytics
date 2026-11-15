# Executive Memo — CredResolve Collections Analytics

**Prepared by:** Aditya Dwivedi  
**Submitted to:** CredResolve  
**Coverage:** Supplied payment events, 1 January–8 August 2026 (August partial)

## Executive decision

The revised Golden Payments fact contains **17,534 accepted successful positive payments**, **13,284 paying accounts**, and **₹131.56 crore gross successful payment value**. This is the final payment_id-based result and supersedes the earlier preliminary payment_reference-deduplicated figure of 12,506 rows / ₹93.60 crore.

The headline statement that “recovery improved by 11% month-on-month” is **not verifiable as a sustained recovery-rate claim**. March 2026 gross successful payment value increased **11.03%** from February, but this is one monthly movement in gross amount. January–July gross recovery was effectively flat (+0.01%). The required historical eligible opening-balance denominator and official KPI definition are absent.

## Historical work and key findings

### 1. Initial source profiling and Phase 1 audit
- 18 CSV files were profiled: 17 operational datasets plus a data dictionary.
- Initial counts included 30,600 borrower rows / 11,015 distinct borrower IDs; 30,000 agent rows / 1,000 distinct agent IDs; 30,000 unique account IDs; and 25,500 payment source rows / 25,000 distinct payment IDs.
- Borrower identifiers were highly non-unique: 8,185 IDs had multiple names, 8,399 multiple phone values, and 8,334 multiple email values.
- Account master contained 455 missing borrower IDs.
- The initial Phase 1 relationship audit showed severe event-to-account borrower mismatches. These were retained as exceptions rather than repaired by guessing.

### 2. Revised payment forensics and Golden Dataset
- `payment_id` is the current transaction key; repeated `payment_reference` values are diagnostic flags, not proof of duplicate transactions.
- 25,500 raw source rows reduce to 25,000 canonical payment IDs; 500 repeated source rows were consolidated after inspected non-null attributes agreed.
- There are zero payment_id conflict groups in the current Golden build.
- 17,534 positive SUCCESS rows form the accepted Golden Payments fact, totaling ₹1,315,583,964.64 (₹131.56 Cr).
- 254 Golden rows have missing payment references; 3,968 Golden rows have reused references. These are flagged, not automatically removed.
- Processor confirmation that `payment_id` is immutable and globally unique remains a required control.

### 3. Historical monthly performance
| Month | Successful payments | Paying accounts | Gross recovery | MoM |
|---|---:|---:|---:|---:|
| Jan-26 | 2,464 | 2,374 | ₹18.72 Cr | — |
| Feb-26 | 2,268 | 2,173 | ₹17.01 Cr | -9.13% |
| Mar-26 | 2,524 | 2,419 | ₹18.89 Cr | +11.03% |
| Apr-26 | 2,406 | 2,304 | ₹17.51 Cr | -7.29% |
| May-26 | 2,449 | 2,344 | ₹18.43 Cr | +5.20% |
| Jun-26 | 2,366 | 2,286 | ₹17.56 Cr | -4.72% |
| Jul-26 | 2,441 | 2,335 | ₹18.72 Cr | +6.65% |
| Aug-26* | 616 | 608 | ₹4.71 Cr | -74.84%* |

*August is partial through 8 August 2026 and must not be compared with a complete month. The supplied payment history covers only January–August 2026; it does not provide a complete 12-month history.*

January–July: gross recovery +0.01%; payment transactions -0.93%; paying accounts -1.64%; average transaction amount +0.95%; recovery per paying account +1.68%; transactions per paying account +0.72%.

### 4. Identity, operational and attribution limitations
- Account master: 30,000 unique account IDs; 455 missing borrower IDs.
- Account/event identity crosswalk: 485,948 exception pairs, 478,379 mismatches and 7,569 matches. Do not force-match borrower identities.
- Agent master: 1,000 agent IDs and 1,099 employee codes; ambiguous many-to-many mapping. Call-agent mapping coverage is approximately 27.62% for calls and 27.65% for call attempts.
- Call, attempt and disposition IDs do not support a reliable end-to-end funnel. PTP has no direct payment foreign key; field visit PAID is not verified payment.
- Campaign targeting: only 19.69% of daily_targeting rows fall within campaign dates; 46.41% are after campaign end and 33.90% before campaign start. No campaign reaches 50% date validity.
- Channel-to-payment associations are descriptive only because populations overlap and exposure is not randomized. 92.26% of accounts were exposed to at least four channels; 66.27% to five or six.

## Forecasting

The model comparison uses daily Golden payment amounts from 1 January–8 August 2026 (220 observations), a 28-day lookback and a chronological 28-day holdout. GRU has the lowest error among the neural models in the current single holdout and beats the 7-day mean baseline; this is preliminary and requires rolling-origin validation. AdamW underperformed the naive baseline in its separate experiment.

GRU provisional gross payment projections: Sep-26 ₹15.67 Cr; Oct-26 ₹15.39 Cr; Nov-26 ₹14.47 Cr; Dec-26 ₹15.66 Cr; Jan-27 ₹17.16 Cr; Feb-27 ₹17.12 Cr. These are forecasts, not actual historical figures, incremental lift, net recovery or ROI.

## SWOT summary

**Strengths:** revised payment_id Golden fact; payment exception and identity forensics; monthly performance reconstruction; reproducible analytical outputs.

**Weaknesses:** incomplete historical window; missing recovery-rate denominator; borrower/agent identity conflicts; weak event linkage; unreliable campaign dates; missing costs.

**Opportunities:** repair identity and event instrumentation; governed metric registry; randomized targeting pilot; cost and customer-outcome measurement.

**Threats:** misleading headline KPI; premature capital deployment; false attribution and inflated metrics; contact fatigue and compliance exposure.

## ₹10 crore recommendation

Do **not** deploy the full ₹10 crore immediately. Prioritize better borrower targeting as a controlled **6–8 week stratified randomized pilot** against business-as-usual. Measure 30-day incremental net recovery per eligible assigned account, with 60-day maturity sensitivity; deduct all intervention costs and monitor complaints, opt-outs, reversals and contact pressure. Scale only when causal incremental net benefit and guardrails are demonstrated. A numeric ROI cannot be responsibly stated from the supplied data.

## Management actions
1. Obtain the missing extracts for the exact intended 12-month reporting window.
2. Obtain the official recovery KPI definition and historical eligible opening-balance snapshots.
3. Confirm payment_id immutability with the processor.
4. Govern borrower and agent crosswalks with effective dates and review status.
5. Repair campaign, call, message and PTP event keys.
6. Capture intervention costs and customer-outcome guardrails.
7. Run the randomized pilot and rolling-origin forecast validation before committing full capital.


## Submission repository reference

GitHub account: [Adityad2018](https://github.com/Adityad2018). Suggested repository: `CredResolve-Collections-Analytics`. The repository URL is pending publication; this package does not claim that a remote repository has already been created or pushed. See `docs/GITHUB_PUBLISHING.md` for the publishing steps.
