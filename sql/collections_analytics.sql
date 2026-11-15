-- CredResolve production-oriented analytical SQL (SQLite 3.25+)
-- Run against data/processed/collections.db. Raw source tables are immutable.
-- Critical rule: payment_id is the transaction key. payment_reference is NOT a dedupe key.

DROP VIEW IF EXISTS payment_id_conflict_groups;
CREATE VIEW payment_id_conflict_groups AS
SELECT payment_id,
       COUNT(*) AS source_rows,
       COUNT(DISTINCT account_id) AS account_variants,
       COUNT(DISTINCT amount) AS amount_variants,
       COUNT(DISTINCT payment_status) AS status_variants,
       COUNT(DISTINCT event_at) AS event_time_variants
FROM raw_payments
WHERE payment_id IS NOT NULL AND TRIM(payment_id) <> ''
GROUP BY payment_id
HAVING COUNT(DISTINCT account_id) > 1
    OR COUNT(DISTINCT amount) > 1
    OR COUNT(DISTINCT payment_status) > 1
    OR COUNT(DISTINCT event_at) > 1;

DROP VIEW IF EXISTS canonical_payments;
CREATE VIEW canonical_payments AS
WITH grouped AS (
  SELECT payment_id,
         MAX(account_id) AS account_id,
         MAX(borrower_id) AS borrower_id,
         MAX(event_at) AS event_at,
         MAX(payment_reference) AS payment_reference,
         MAX(CAST(amount AS REAL)) AS amount,
         MAX(payment_status) AS payment_status,
         MAX(payment_method) AS payment_method,
         MAX(provider_id) AS provider_id,
         COUNT(*) AS source_rows,
         COUNT(DISTINCT account_id) AS account_variants,
         COUNT(DISTINCT amount) AS amount_variants,
         COUNT(DISTINCT payment_status) AS status_variants,
         COUNT(DISTINCT event_at) AS event_time_variants
  FROM raw_payments
  WHERE payment_id IS NOT NULL AND TRIM(payment_id) <> ''
  GROUP BY payment_id
)
SELECT g.*,
       CASE WHEN g.account_variants<=1 AND g.amount_variants<=1
                  AND g.status_variants<=1 AND g.event_time_variants<=1
            THEN 1 ELSE 0 END AS is_nonconflicting
FROM grouped g;

DROP VIEW IF EXISTS golden_successful_payments;
CREATE VIEW golden_successful_payments AS
SELECT payment_id, account_id, borrower_id, event_at, payment_reference,
       amount, payment_status, payment_method, provider_id, source_rows
FROM canonical_payments
WHERE is_nonconflicting=1
  AND UPPER(TRIM(COALESCE(payment_status,'')))='SUCCESS'
  AND COALESCE(amount,0)>0;

DROP VIEW IF EXISTS monthly_recovery;
CREATE VIEW monthly_recovery AS
SELECT substr(event_at,1,7) AS month,
       COUNT(*) AS successful_payment_count,
       COUNT(DISTINCT account_id) AS unique_paying_accounts,
       SUM(amount) AS successful_recovery_amount
FROM golden_successful_payments
GROUP BY substr(event_at,1,7);

DROP VIEW IF EXISTS payment_reference_quality;
CREATE VIEW payment_reference_quality AS
SELECT payment_reference,
       COUNT(*) AS canonical_payment_ids,
       COUNT(DISTINCT account_id) AS account_count,
       SUM(amount) AS gross_amount,
       CASE WHEN payment_reference IS NULL OR TRIM(payment_reference)=''
            THEN 'MISSING' ELSE 'PRESENT' END AS reference_status
FROM canonical_payments
WHERE is_nonconflicting=1
GROUP BY payment_reference;

DROP VIEW IF EXISTS account_borrower_exceptions;
CREATE VIEW account_borrower_exceptions AS
SELECT p.payment_id, p.account_id,
       p.borrower_id AS payment_borrower_id,
       a.borrower_id AS master_borrower_id,
       CASE WHEN p.borrower_id IS NULL OR a.borrower_id IS NULL THEN 'MISSING'
            WHEN p.borrower_id=a.borrower_id THEN 'MATCH'
            ELSE 'MISMATCH' END AS identity_status
FROM golden_successful_payments p
LEFT JOIN raw_accounts a ON p.account_id=a.account_id;

DROP VIEW IF EXISTS campaign_target_date_audit;
CREATE VIEW campaign_target_date_audit AS
SELECT t.target_id,t.account_id,t.campaign_id,t.target_date,
       c.start_at,c.end_at,
       CASE WHEN c.campaign_id IS NULL THEN 'NO_CAMPAIGN_MATCH'
            WHEN date(t.target_date)<date(c.start_at) THEN 'BEFORE_START'
            WHEN date(t.target_date)>date(c.end_at) THEN 'AFTER_END'
            ELSE 'WITHIN_DATES' END AS date_status
FROM raw_daily_targeting t
LEFT JOIN raw_campaigns c ON t.campaign_id=c.campaign_id;

DROP VIEW IF EXISTS monthly_call_descriptives;
CREATE VIEW monthly_call_descriptives AS
SELECT substr(event_at,1,7) AS month, COUNT(*) AS call_rows,
       SUM(CASE WHEN UPPER(call_status)='ANSWERED' THEN 1 ELSE 0 END) AS answered_rows
FROM raw_calls GROUP BY substr(event_at,1,7);
-- Deliberately no RPC, PTP-kept, channel conversion, cost/recovery or agent-hour KPI:
-- source keys, disposition semantics, payment linkage, costs or reliable agent identity are absent.

-- Reconciliation checks (run after views are created):
-- SELECT COUNT(*) FROM golden_successful_payments; -- expected 17,534 on supplied extract
-- SELECT ROUND(SUM(amount),2) FROM golden_successful_payments; -- expected 1,315,583,964.64
-- SELECT COUNT(*) FROM payment_id_conflict_groups; -- expected 0
-- SELECT month,successful_payment_count,unique_paying_accounts,ROUND(successful_recovery_amount,2)
-- FROM monthly_recovery ORDER BY month;
