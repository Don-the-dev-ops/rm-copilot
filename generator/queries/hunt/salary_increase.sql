SELECT a.client_id,
       MIN(t.amount_zar) AS lowest_salary,
       MAX(t.amount_zar) AS highest_salary,
       ROUND((MAX(t.amount_zar) / MIN(t.amount_zar) - 1) * 100, 1) AS raise_pct
FROM transactions t
JOIN accounts a ON a.account_id = t.account_id
WHERE t.merchant_category = 'income'
GROUP BY a.client_id
HAVING MAX(t.amount_zar) > MIN(t.amount_zar)
ORDER BY raise_pct DESC;