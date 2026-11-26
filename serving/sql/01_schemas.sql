-- RM Copilot, Phase 5 Lab 13: three schemas, one per job.
-- Safe to re-run: each schema is created only if it is missing.
IF SCHEMA_ID('stg')   IS NULL EXEC('CREATE SCHEMA stg');    -- stockroom: raw copy of each CSV, refilled every load
IF SCHEMA_ID('serve') IS NULL EXEC('CREATE SCHEMA serve');  -- shelves: trusted Gold rows, changed only by MERGE
IF SCHEMA_ID('app')   IS NULL EXEC('CREATE SCHEMA app');    -- shop window: views the app reads, plus the brief log
