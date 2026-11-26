-- RM Copilot, Lab 15: add card balances to the serving layer.
-- A migration: changes an existing database in place, safe to re-run (each column is added only if missing).
-- Fresh databases get the same columns from 02_tables.sql.

IF COL_LENGTH('stg.client_360', 'card_balance_zar') IS NULL
    ALTER TABLE stg.client_360 ADD card_balance_zar DECIMAL(18,2) NULL;      -- what the client owes on credit cards today
IF COL_LENGTH('stg.client_360', 'card_utilisation_pct') IS NULL
    ALTER TABLE stg.client_360 ADD card_utilisation_pct DECIMAL(5,1) NULL;   -- card balance as % of credit limit

IF COL_LENGTH('serve.client_360', 'card_balance_zar') IS NULL
    ALTER TABLE serve.client_360 ADD card_balance_zar DECIMAL(18,2) NULL;
IF COL_LENGTH('serve.client_360', 'card_utilisation_pct') IS NULL
    ALTER TABLE serve.client_360 ADD card_utilisation_pct DECIMAL(5,1) NULL;
GO
