-- Collections Analytics | Phase 1 SQL checks (SQLite)
-- Run after: python src/run_phase1.py
-- Database: data/processed/collections.db
-- Open with DB Browser for SQLite or sqlite3.

-- 1. Table row counts
SELECT 'borrowers' AS table_name, COUNT(*) AS rows FROM borrowers
UNION ALL SELECT 'agents', COUNT(*) FROM agents
UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL SELECT 'payments', COUNT(*) FROM payments;

-- 2. Candidate key checks
SELECT COUNT(*) AS rows, COUNT(DISTINCT borrower_id) AS unique_ids,
       COUNT(*) - COUNT(DISTINCT borrower_id) AS repeated_id_rows
FROM borrowers;

SELECT COUNT(*) AS rows, COUNT(DISTINCT agent_id) AS unique_ids,
       COUNT(*) - COUNT(DISTINCT agent_id) AS repeated_id_rows
FROM agents;

SELECT COUNT(*) AS rows, COUNT(DISTINCT account_id) AS unique_ids,
       COUNT(*) - COUNT(DISTINCT account_id) AS repeated_id_rows
FROM accounts;

SELECT COUNT(*) AS rows, COUNT(DISTINCT payment_id) AS unique_ids,
       COUNT(*) - COUNT(DISTINCT payment_id) AS repeated_id_rows
FROM payments;

-- 3. Borrower IDs linked to multiple names / contact values
SELECT borrower_id, COUNT(*) AS records,
       COUNT(DISTINCT name) AS names,
       COUNT(DISTINCT phone) AS phones,
       COUNT(DISTINCT email) AS emails
FROM borrowers
GROUP BY borrower_id
HAVING COUNT(*) > 1
ORDER BY records DESC;

-- 4. Agent IDs linked to multiple names / employee codes / vendors
SELECT agent_id, COUNT(*) AS records,
       COUNT(DISTINCT agent_name) AS names,
       COUNT(DISTINCT employee_code) AS employee_codes,
       COUNT(DISTINCT vendor_id) AS vendors
FROM agents
GROUP BY agent_id
HAVING COUNT(*) > 1
ORDER BY records DESC;

-- 5. Payment ID duplicates: inspect before deciding whether true duplicates
SELECT payment_id, COUNT(*) AS records,
       COUNT(DISTINCT payment_reference) AS references,
       COUNT(DISTINCT amount) AS amounts,
       COUNT(DISTINCT status) AS statuses
FROM payments
GROUP BY payment_id
HAVING COUNT(*) > 1
ORDER BY records DESC;

-- 6. Account-to-borrower mismatch in payments
WITH account_map AS (
    SELECT DISTINCT account_id, borrower_id FROM accounts
),
payment_pairs AS (
    SELECT DISTINCT account_id, borrower_id
    FROM payments
    WHERE account_id IS NOT NULL AND borrower_id IS NOT NULL
)
SELECT COUNT(*) AS distinct_event_pairs,
       SUM(CASE WHEN a.account_id IS NULL THEN 1 ELSE 0 END) AS account_not_found,
       SUM(CASE WHEN a.account_id IS NOT NULL
                 AND p.borrower_id <> a.borrower_id THEN 1 ELSE 0 END) AS borrower_mismatch
FROM payment_pairs p
LEFT JOIN account_map a ON p.account_id = a.account_id;

-- 7. Missing borrower attributes
SELECT
  SUM(CASE WHEN borrower_id IS NULL THEN 1 ELSE 0 END) AS missing_borrower_id,
  SUM(CASE WHEN name IS NULL THEN 1 ELSE 0 END) AS missing_name,
  SUM(CASE WHEN phone IS NULL THEN 1 ELSE 0 END) AS missing_phone,
  SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS missing_email
FROM borrowers;
