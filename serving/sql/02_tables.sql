-- RM Copilot, Phase 5 Lab 13: staging, serving and log tables.
-- Safe to re-run: each table is created only if it is missing.
-- Type rules: money DECIMAL(18,2), flags BIT, dates DATE, timestamps DATETIME2, ids VARCHAR.

GO
------------------------------------------------------------------ client_360
IF OBJECT_ID('stg.client_360') IS NULL
CREATE TABLE stg.client_360 (
    client_id              VARCHAR(20)    NULL,   -- staging allows NULLs: the loader checks, not the table
    first_name             NVARCHAR(60)   NULL,
    last_name              NVARCHAR(60)   NULL,
    segment                NVARCHAR(30)   NULL,
    risk_profile           NVARCHAR(20)   NULL,
    city                   NVARCHAR(60)   NULL,
    province               NVARCHAR(40)   NULL,
    age                    INT            NULL,
    years_as_client        INT            NULL,
    monthly_income_zar     DECIMAL(18,2)  NULL,
    rm_id                  VARCHAR(10)    NULL,
    rm_name                NVARCHAR(100)  NULL,
    branch                 NVARCHAR(60)   NULL,
    main_balance_zar       DECIMAL(18,2)  NULL,
    tfsa_balance_zar       DECIMAL(18,2)  NULL,
    offshore_balance_usd   DECIMAL(18,2)  NULL,
    account_count          INT            NULL,
    credit_limit_zar       DECIMAL(18,2)  NULL,
    loan_count             INT            NULL,
    loans_outstanding_zar  DECIMAL(18,2)  NULL,
    has_home_loan          BIT            NULL,
    has_vehicle_finance    BIT            NULL,
    debt_to_annual_income  DECIMAL(9,2)   NULL,
    last_txn_date          DATE           NULL,
    spend_last_90d_zar     DECIMAL(18,2)  NULL,
    txns_last_90d          INT            NULL
);

IF OBJECT_ID('serve.client_360') IS NULL
CREATE TABLE serve.client_360 (
    client_id              VARCHAR(20)    NOT NULL CONSTRAINT pk_client_360 PRIMARY KEY,
    first_name             NVARCHAR(60)   NOT NULL,
    last_name              NVARCHAR(60)   NOT NULL,
    segment                NVARCHAR(30)   NOT NULL,
    risk_profile           NVARCHAR(20)   NULL,
    city                   NVARCHAR(60)   NULL,
    province               NVARCHAR(40)   NULL,
    age                    INT            NULL,
    years_as_client        INT            NULL,
    monthly_income_zar     DECIMAL(18,2)  NULL,
    rm_id                  VARCHAR(10)    NULL,
    rm_name                NVARCHAR(100)  NULL,
    branch                 NVARCHAR(60)   NULL,
    main_balance_zar       DECIMAL(18,2)  NULL,
    tfsa_balance_zar       DECIMAL(18,2)  NULL,
    offshore_balance_usd   DECIMAL(18,2)  NULL,
    account_count          INT            NULL,
    credit_limit_zar       DECIMAL(18,2)  NULL,
    loan_count             INT            NULL,
    loans_outstanding_zar  DECIMAL(18,2)  NULL,
    has_home_loan          BIT            NULL,
    has_vehicle_finance    BIT            NULL,
    debt_to_annual_income  DECIMAL(9,2)   NULL,
    last_txn_date          DATE           NULL,
    spend_last_90d_zar     DECIMAL(18,2)  NULL,
    txns_last_90d          INT            NULL,
    _loaded_at             DATETIME2(0)   NOT NULL CONSTRAINT df_client_360_loaded DEFAULT SYSUTCDATETIME()
);

GO
------------------------------------------------------------------ client_signals
IF OBJECT_ID('stg.client_signals') IS NULL
CREATE TABLE stg.client_signals (
    client_id              VARCHAR(20)    NULL,
    idle_cash              BIT            NULL,
    idle_months_of_income  DECIMAL(9,1)   NULL,
    forex_growth           BIT            NULL,
    forex_trips_first_3m   INT            NULL,
    forex_trips_last_3m    INT            NULL,
    upgrade_candidate      BIT            NULL,
    salary_increase        BIT            NULL,
    lowest_salary_zar      DECIMAL(18,2)  NULL,
    highest_salary_zar     DECIMAL(18,2)  NULL,
    salary_raise_pct       DECIMAL(9,1)   NULL,
    anomaly                BIT            NULL,
    anomaly_txn_count      INT            NULL,
    anomaly_largest_zar    DECIMAL(18,2)  NULL,
    signal_count           INT            NULL
);

IF OBJECT_ID('serve.client_signals') IS NULL
CREATE TABLE serve.client_signals (
    client_id              VARCHAR(20)    NOT NULL CONSTRAINT pk_client_signals PRIMARY KEY,
    idle_cash              BIT            NOT NULL,
    idle_months_of_income  DECIMAL(9,1)   NULL,
    forex_growth           BIT            NOT NULL,
    forex_trips_first_3m   INT            NULL,
    forex_trips_last_3m    INT            NULL,
    upgrade_candidate      BIT            NOT NULL,
    salary_increase        BIT            NOT NULL,
    lowest_salary_zar      DECIMAL(18,2)  NULL,
    highest_salary_zar     DECIMAL(18,2)  NULL,
    salary_raise_pct       DECIMAL(9,1)   NULL,
    anomaly                BIT            NOT NULL,
    anomaly_txn_count      INT            NOT NULL,
    anomaly_largest_zar    DECIMAL(18,2)  NULL,
    signal_count           INT            NOT NULL,
    _loaded_at             DATETIME2(0)   NOT NULL CONSTRAINT df_client_signals_loaded DEFAULT SYSUTCDATETIME()
);

GO
------------------------------------------------------------------ anomaly_transactions
IF OBJECT_ID('stg.anomaly_transactions') IS NULL
CREATE TABLE stg.anomaly_transactions (
    client_id              VARCHAR(20)    NULL,
    txn_id                 VARCHAR(30)    NULL,
    txn_ts                 DATETIME2(0)   NULL,   -- UTC, as stored in Silver
    txn_date_sast          DATE           NULL,
    txn_hour_sast          INT            NULL,
    amount_zar             DECIMAL(18,2)  NULL,   -- negative = money out
    merchant_name          NVARCHAR(120)  NULL,
    country_code           CHAR(2)        NULL,
    channel                NVARCHAR(20)   NULL
);

IF OBJECT_ID('serve.anomaly_transactions') IS NULL
CREATE TABLE serve.anomaly_transactions (
    txn_id                 VARCHAR(30)    NOT NULL CONSTRAINT pk_anomaly_transactions PRIMARY KEY,
    client_id              VARCHAR(20)    NOT NULL,
    txn_ts                 DATETIME2(0)   NOT NULL,
    txn_date_sast          DATE           NOT NULL,
    txn_hour_sast          INT            NOT NULL,
    amount_zar             DECIMAL(18,2)  NOT NULL,
    merchant_name          NVARCHAR(120)  NULL,
    country_code           CHAR(2)        NULL,
    channel                NVARCHAR(20)   NULL,
    _loaded_at             DATETIME2(0)   NOT NULL CONSTRAINT df_anomaly_loaded DEFAULT SYSUTCDATETIME()
);

GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_anomaly_client')
CREATE INDEX ix_anomaly_client ON serve.anomaly_transactions (client_id);  -- the client page looks up by client

GO
------------------------------------------------------------------ load_log (one row per table per run)
IF OBJECT_ID('serve.load_log') IS NULL
CREATE TABLE serve.load_log (
    log_id         INT IDENTITY(1,1)  NOT NULL CONSTRAINT pk_load_log PRIMARY KEY,
    run_id         UNIQUEIDENTIFIER   NOT NULL,   -- same for every table in one loader run
    table_name     VARCHAR(60)        NOT NULL,
    source_file    NVARCHAR(260)      NOT NULL,
    rows_in_file   INT                NULL,
    rows_staged    INT                NULL,
    rows_inserted  INT                NULL,
    rows_updated   INT                NULL,
    rows_deleted   INT                NULL,
    status         VARCHAR(10)        NOT NULL,   -- success | failed
    message        NVARCHAR(400)      NULL,
    started_at     DATETIME2(0)       NOT NULL,
    finished_at    DATETIME2(0)       NULL
);

GO
------------------------------------------------------------------ brief_log (filled from Lab 14)
IF OBJECT_ID('app.brief_log') IS NULL
CREATE TABLE app.brief_log (
    brief_id        INT IDENTITY(1,1)  NOT NULL CONSTRAINT pk_brief_log PRIMARY KEY,
    client_id       VARCHAR(20)        NOT NULL,
    model           VARCHAR(100)       NOT NULL,
    prompt_version  VARCHAR(20)        NOT NULL,
    brief_text      NVARCHAR(MAX)      NOT NULL,
    input_tokens    INT                NULL,
    output_tokens   INT                NULL,
    created_at      DATETIME2(0)       NOT NULL CONSTRAINT df_brief_created DEFAULT SYSUTCDATETIME()
);
GO
