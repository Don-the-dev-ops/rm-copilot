SELECT txn_id, txn_ts, amount_zar, merchant_name, country_code, channel
FROM transactions
WHERE channel = 'Online'
  AND country_code <> 'ZA'
  AND amount_zar <= -40000
  AND CAST(substr(txn_ts, 12, 2) AS INTEGER) < 6
ORDER BY amount_zar;