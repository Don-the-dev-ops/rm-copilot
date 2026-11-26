-- RM Copilot, Phase 5 Lab 13: the app's contract. The app reads these views, never serve.* directly.
-- CREATE OR ALTER makes every view safe to re-run.
GO
CREATE OR ALTER VIEW app.v_client_list AS
-- One line per client for the list page.
SELECT c.client_id,
       c.first_name + N' ' + c.last_name                    AS client_name,
       c.segment, c.rm_id, c.rm_name, c.branch, c.city,
       c.main_balance_zar + c.tfsa_balance_zar               AS total_zar_balance,
       c.offshore_balance_usd,
       s.signal_count,
       CASE                                                  -- one headline reason to call, risk first
           WHEN s.anomaly = 1           THEN N'Possible fraud'
           WHEN s.idle_cash = 1         THEN N'Idle cash'
           WHEN s.upgrade_candidate = 1 THEN N'Upgrade candidate'
           WHEN s.salary_increase = 1   THEN N'Salary increase'
           WHEN s.forex_growth = 1      THEN N'Forex growth'
           ELSE N'No action today'
       END                                                   AS top_signal,
       c.last_txn_date
FROM serve.client_360 c
JOIN serve.client_signals s ON s.client_id = c.client_id;
GO
CREATE OR ALTER VIEW app.v_client_detail AS
-- Everything about one client: the client page and the AI brief both read this.
SELECT c.client_id, c.first_name, c.last_name, c.segment, c.risk_profile, c.city, c.province,
       c.age, c.years_as_client, c.monthly_income_zar,
       c.rm_id, c.rm_name, c.branch,
       c.main_balance_zar, c.tfsa_balance_zar, c.offshore_balance_usd, c.account_count,
       c.credit_limit_zar, c.loan_count, c.loans_outstanding_zar, c.has_home_loan, c.has_vehicle_finance,
       c.debt_to_annual_income, c.last_txn_date, c.spend_last_90d_zar, c.txns_last_90d,
       s.signal_count,
       s.idle_cash, s.idle_months_of_income,
       s.forex_growth, s.forex_trips_first_3m, s.forex_trips_last_3m,
       s.upgrade_candidate,
       s.salary_increase, s.lowest_salary_zar, s.highest_salary_zar, s.salary_raise_pct,
       s.anomaly, s.anomaly_txn_count, s.anomaly_largest_zar,
       c._loaded_at AS data_as_of
FROM serve.client_360 c
JOIN serve.client_signals s ON s.client_id = c.client_id;
GO
CREATE OR ALTER VIEW app.v_client_anomalies AS
-- A client's flagged transactions; the app sorts newest first.
SELECT a.client_id, a.txn_id, a.txn_ts AS txn_ts_utc, a.txn_date_sast, a.txn_hour_sast,
       -a.amount_zar AS amount_out_zar,                      -- shown as a positive amount leaving the account
       a.merchant_name, a.country_code, a.channel
FROM serve.anomaly_transactions a;
GO
