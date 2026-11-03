SELECT client_id, segment, monthly_income_zar
FROM clients
WHERE segment = 'Private Banking'
  AND monthly_income_zar >= 92000
ORDER BY monthly_income_zar DESC;