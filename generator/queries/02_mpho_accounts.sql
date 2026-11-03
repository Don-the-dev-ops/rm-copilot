SELECT c.first_name, c.last_name, a.product, a.balance
FROM clients c
JOIN accounts a ON a.client_id = c.client_id
WHERE c.client_id = 'CL-b38a088ca6';