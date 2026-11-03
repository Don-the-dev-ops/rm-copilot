SELECT c.first_name, c.last_name, l.loan_type, l.principal_zar, l.outstanding_zar
FROM clients c
JOIN loans l ON l.client_id = c.client_id
WHERE c.client_id = 'CL-b38a088ca6';