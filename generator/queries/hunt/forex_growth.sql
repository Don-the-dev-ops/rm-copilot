SELECT a.client_id,
       SUM(CASE WHEN t.txn_ts <  '2026-01-07' THEN 1 ELSE 0 END) AS trips_first_3_months,
       SUM(CASE WHEN t.txn_ts >= '2026-07-09' THEN 1 ELSE 0 END) AS trips_last_3_months
FROM transactions t
JOIN accounts a ON a.account_id = t.account_id
WHERE t.merchant_category = 'travel_foreign'
GROUP BY a.client_id
HAVING trips_last_3_months >= 8
ORDER BY trips_last_3_months DESC;