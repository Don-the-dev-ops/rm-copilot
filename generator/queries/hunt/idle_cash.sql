SELECT c.client_id, c.monthly_income_zar, a.balance,
       ROUND(a.balance / c.monthly_income_zar, 1) AS months_of_income
FROM clients c
JOIN accounts a ON a.client_id = c.client_id
WHERE a.product IN ('Private Banking Account', 'Signature Account')
  AND a.balance > 4 * c.monthly_income_zar
ORDER BY months_of_income DESC;