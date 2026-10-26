# Booking Repository Reporting Database

## Overview

This database provides a local reporting repository for booking data copied from an existing booking-system repository. The database mirrors the required source schema, pipelines data into local tables through stored procedures, records incremental execution state in an `ETL_Watermark` table, and produces reporting-ready summary tables.

BI and Reporting Platforms consume database views rather than querying raw replicated tables directly. This separates ingestion logic from reporting logic and provides a stable reporting contract when underlying tables or transformations change.

The general data flow is:

```text
Source Booking Repository
          |
          v
Schema-Compatible Raw Tables
          |
          v
Nightly Stored Procedure Pipeline
          |
          +---- ETL_Watermark / Run Logging
          |
          v
Cleaned and Consolidated Booking Tables
          |
          v
Reporting Summary Tables
          |
          v
Reporting Views
          |
          +---- BI Platforms
          +---- Reporting Platforms
```

---

## Objectives

The database is designed to:

- Preserve required booking data outside the operational repository.
- Reproduce the source structures needed by the reporting pipeline.
- Load new and changed records incrementally.
- track pipeline progress through an `ETL_Watermark` table.
- Maintain booking history where required.
- Create clean, consolidated booking records for reporting.
- Precalculate frequently used booking summaries.
- Present stable views to BI and Reporting Platforms.
- Reduce reporting load and dependency on the source booking repository.
- Support validation, troubleshooting, auditing, and controlled recovery.

---

## Database Layers

A layered design keeps source replication, transformation, reporting, and administration responsibilities separate.

### Raw or Source-Mirror Layer

Contains local tables that reproduce the required schema from the booking repository.

Responsibilities:

- Preserve source-compatible column names and data types.
- Store copied source records with minimal business transformation.
- Support repeatable incremental loads.
- Retain source identifiers and source modification timestamps.
- Act as the starting point for downstream transformations.

Suggested schema:

```text
src
```

Example objects:

```text
src.BookingHistory
src.Bookings
src.Drivers
src.Vehicles
src.Accounts
src.Companies
```

### Staging Layer

Contains temporary or intermediate data used by stored procedures during a pipeline run.

Responsibilities:

- Receive data from the source repository.
- Deduplicate incoming records.
- Normalize source values.
- Compare incoming data with existing target rows.
- Isolate incomplete batches before they affect reporting tables.

Suggested schema:

```text
stg
```

Example objects:

```text
stg.BookingHistory
stg.Bookings
stg.BookingChanges
```

### Reporting and Summary Layer

Contains cleaned, consolidated, or aggregated tables optimized for reporting.

Responsibilities:

- Produce the current or final state of each booking.
- Resolve source history into reportable booking records.
- Store commonly used daily, weekly, monthly, market, account, and service summaries.
- Reduce repeated calculations in BI and Reporting Platforms.

Suggested schema:

```text
rpt
```

Example objects:

```text
rpt.Booking
rpt.BookingDailySummary
rpt.BookingMarketSummary
rpt.BookingAccountSummary
rpt.BookingServiceSummary
```

### Administration Layer

Contains ETL control, monitoring, and audit objects.

Suggested schema:

```text
adm
```

Example objects:

```text
adm.ETL_Watermark
adm.ETL_Run
adm.ETL_RunStep
adm.ETL_Error
```

### View Layer

Contains the stable database interface used by reports.

Suggested schema:

```text
report
```

Example objects:

```text
report.vw_Bookings
report.vw_BookingDailySummary
report.vw_BookingMarketSummary
report.vw_BookingAccountSummary
```

---

## Database Creation Process

### 1. Inventory the Source Repository

Before creating the new database, document the source objects required by the pipeline.

For each source table, record:

- Schema name
- Table name
- Column names
- SQL Server data types
- Nullability
- Default constraints
- Primary key
- Unique constraints
- Foreign keys
- Indexes
- Identity properties
- Computed columns
- Triggers
- Row counts
- Candidate incremental-load column
- Source retention behavior

Only reproduce objects required for ingestion, transformation, reconciliation, or reporting. The target database does not need to copy unrelated application objects.

### 2. Create the Database

Create the SQL Server database using the organization's normal naming, file placement, recovery, backup, and security standards.

Example naming pattern:

```text
Booking_<RepositoryID>
```

The first successfully validated database can be used as the template for additional booking repositories.

### 3. Create Schemas

Example:

```sql
CREATE SCHEMA src AUTHORIZATION dbo;
CREATE SCHEMA stg AUTHORIZATION dbo;
CREATE SCHEMA rpt AUTHORIZATION dbo;
CREATE SCHEMA adm AUTHORIZATION dbo;
CREATE SCHEMA report AUTHORIZATION dbo;
GO
```

### 4. Recreate Required Source Tables

Generate `CREATE TABLE` statements from the existing repository and deploy them to the raw or source-mirror schema.

The recreated tables should preserve the source characteristics needed by the pipeline, including:

- Compatible column types and lengths
- Precision and scale
- Nullability
- Primary or natural keys
- Source timestamps
- Relationships required by transformation logic

Review source indexes before copying all of them. Operational-system indexes may not match the access patterns of a reporting repository. Retain integrity indexes, then add reporting and ETL indexes based on measured query patterns.

### 5. Create ETL Control Tables

Create the watermark, run-log, step-log, and error tables before deploying the pipelines.

### 6. Deploy Stored Procedures

Deploy stored procedures for:

- Source extraction
- Staging loads
- Raw-table merges
- Booking consolidation
- Summary refreshes
- Validation
- Watermark updates
- Error logging

### 7. Perform the Initial Load

The initial load establishes the baseline copy of source data.

Recommended sequence:

1. Create the target structures.
2. Disable or defer nonessential secondary indexes when appropriate.
3. Load the required source history.
4. Validate source-to-target counts and keys.
5. Build or rebuild indexes.
6. Populate consolidated booking tables.
7. Populate reporting summary tables.
8. Validate report views.
9. Initialize the watermark only after the load succeeds.

### 8. Schedule the Nightly Pipeline

Use SQL Server Agent or the approved orchestration platform to execute a parent stored procedure each night.

Example:

```text
SQL Server Agent Job
    |
    v
etl.usp_RunNightlyBookingPipeline
    |
    +-- Stage source changes
    +-- Merge raw tables
    +-- Build current booking state
    +-- Refresh summaries
    +-- Run validation
    +-- Commit watermark
```

The parent procedure should stop dependent steps when an earlier critical step fails.

---

## ETL Watermark Design

The `ETL_Watermark` table stores the last successfully committed position for each pipeline or source object. It allows the next run to request only records added or changed after the prior successful execution.

A watermark is pipeline state, not simply a timestamp showing that a procedure started. It should advance only after the relevant data has been committed and validated.

### Suggested Table

```sql
CREATE TABLE adm.ETL_Watermark
(
    WatermarkID           int IDENTITY(1,1) NOT NULL,
    PipelineName          sysname NOT NULL,
    SourceSystem          sysname NOT NULL,
    SourceObject          nvarchar(256) NOT NULL,
    WatermarkColumn       sysname NOT NULL,
    LastWatermarkValue    nvarchar(128) NULL,
    PendingWatermarkValue nvarchar(128) NULL,
    LastStartedAtUtc      datetime2(7) NULL,
    LastSucceededAtUtc    datetime2(7) NULL,
    LastFailedAtUtc       datetime2(7) NULL,
    LastRunID             bigint NULL,
    LastStatus            varchar(20) NULL,
    IsEnabled             bit NOT NULL
        CONSTRAINT DF_ETL_Watermark_IsEnabled DEFAULT (1),
    CreatedAtUtc          datetime2(7) NOT NULL
        CONSTRAINT DF_ETL_Watermark_CreatedAtUtc DEFAULT (SYSUTCDATETIME()),
    UpdatedAtUtc          datetime2(7) NOT NULL
        CONSTRAINT DF_ETL_Watermark_UpdatedAtUtc DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_ETL_Watermark PRIMARY KEY (WatermarkID),
    CONSTRAINT UQ_ETL_Watermark UNIQUE
        (PipelineName, SourceSystem, SourceObject)
);
GO
```

If the source uses a numeric sequence, rowversion, archive timestamp, or source ID instead of a datetime, store and compare the native value where practical. A typed watermark avoids conversion ambiguity.

### Watermark Execution Pattern

```text
1. Read LastWatermarkValue.
2. Capture the source high-water mark for this run.
3. Save it as PendingWatermarkValue.
4. Extract rows greater than the prior watermark and no greater than the captured high-water mark.
5. Load and merge the batch.
6. Run validations.
7. Promote PendingWatermarkValue to LastWatermarkValue.
8. Record success.
```

Capturing a fixed upper bound prevents records arriving during the load from falling between executions.

### Watermark Safety Rules

- Never advance the committed watermark before the target transaction succeeds.
- Do not treat a started procedure as a successful load.
- Use an overlap window if source timestamps can arrive late or have limited precision.
- Make target merges idempotent so overlapped rows can be reprocessed safely.
- Preserve the failed run's attempted range for troubleshooting.
- Do not reset a watermark without documenting the replay range and expected impact.

---

## ETL Run Logging

The watermark indicates where the pipeline stopped. A separate run log explains what happened during each execution.

### Suggested Run Table

```sql
CREATE TABLE adm.ETL_Run
(
    RunID              bigint IDENTITY(1,1) NOT NULL,
    PipelineName       sysname NOT NULL,
    StartedAtUtc       datetime2(7) NOT NULL,
    CompletedAtUtc     datetime2(7) NULL,
    Status             varchar(20) NOT NULL,
    StartingWatermark  nvarchar(128) NULL,
    EndingWatermark    nvarchar(128) NULL,
    RowsExtracted      bigint NULL,
    RowsInserted       bigint NULL,
    RowsUpdated        bigint NULL,
    RowsDeleted        bigint NULL,
    RowsRejected       bigint NULL,
    ErrorNumber        int NULL,
    ErrorMessage       nvarchar(4000) NULL,
    CONSTRAINT PK_ETL_Run PRIMARY KEY (RunID)
);
GO
```

Recommended statuses:

```text
Started
Succeeded
Failed
Skipped
PartiallySucceeded
```

---

## Stored Procedure Pipeline

### Parent Orchestration Procedure

The nightly job should call one parent procedure rather than maintaining complex ETL logic directly in SQL Server Agent steps.

Example:

```sql
EXEC etl.usp_RunNightlyBookingPipeline
    @RepositoryID = 'RepositoryID';
```

The orchestration procedure should:

1. Create an ETL run record.
2. Read the committed watermark.
3. Capture the current source high-water mark.
4. Execute source-specific load procedures.
5. Build the consolidated booking data.
6. Refresh affected summary tables.
7. Execute validation procedures.
8. Commit the watermark.
9. Mark the run successful.
10. Log and throw errors when a critical step fails.

### Suggested Procedure Groups

```text
etl.usp_StageArchivedBookings
etl.usp_MergeArchivedBookings
etl.usp_StageBookings
etl.usp_MergeBookings
etl.usp_BuildBookingBridge
etl.usp_BuildCurrentBookings
etl.usp_RefreshBookingDailySummary
etl.usp_RefreshBookingMarketSummary
etl.usp_ValidateNightlyLoad
etl.usp_RunNightlyBookingPipeline
```

### Transaction Pattern

Use transactions around logically atomic operations, but avoid placing the entire potentially long-running nightly pipeline in one oversized transaction.

```sql
BEGIN TRY
    BEGIN TRANSACTION;

    -- Merge one logical batch.
    -- Validate the batch-level result.

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
```

The watermark should be updated in the final successful control step, after the required data and validation work has completed.

---

## Building the Current Booking Table

The raw repository may contain multiple versions or lifecycle records for one logical booking. Reporting generally requires one consistent row representing the selected current or final state.

A consolidated booking table can:

- Resolve booking history into one reportable record.
- Retain the logical booking identifier.
- Preserve the selected source record identifier.
- Mark the final-state selection.
- Store source and target update timestamps.
- Standardize status, market, account, service, and outcome fields.
- Support incremental rebuilding for only affected bookings.

Example object:

```text
rpt.Booking
```

Suggested keys:

```text
BookingID
LogicalID
SourceBookingID
RepositoryID
```

If the booking system can change identifiers across lifecycle records, maintain a bridge table that explicitly relates the raw historical identifiers to the reporting booking key.

Example:

```text
rpt.BookingBridge
```

Reports should not independently recreate this resolution logic. The database should determine the approved booking state once and expose it consistently.

---

## Reporting Summary Tables

Summary tables should materialize expensive or commonly repeated calculations used by BI and reporting platforms.

Possible grains include:

- Booking date and market
- Booking date and company
- Booking date and account
- Booking date and service type
- Booking date and booking source
- Booking date and outcome
- Driver, vehicle, or fleet period

Example table:

```sql
CREATE TABLE rpt.BookingDailySummary
(
    BookingDate       date NOT NULL,
    RepositoryID      varchar(20) NOT NULL,
    MarketKey         int NOT NULL,
    CompanyID         int NULL,
    AccountID         int NULL,
    EnteredBookings   bigint NOT NULL,
    CompletedBookings bigint NOT NULL,
    CancelledBookings bigint NOT NULL,
    RejectedBookings  bigint NOT NULL,
    LostBookings      bigint NOT NULL,
    RevenueAmount     decimal(19,4) NULL,
    LastRefreshedUtc  datetime2(7) NOT NULL,
    CONSTRAINT PK_BookingDailySummary
        PRIMARY KEY (BookingDate, RepositoryID, MarketKey, CompanyID, AccountID)
);
GO
```

The actual measures and grain must match the organization's approved booking definitions. Avoid mixing facts with different grains in one row unless the relationship is explicit.

### Incremental Summary Refresh

Instead of rebuilding all history every night:

1. Identify the dates or booking keys changed by the incremental load.
2. Delete or update the impacted summary partitions.
3. Reaggregate those periods from the consolidated booking table.
4. Validate detail-to-summary totals.
5. Record the refresh range in the ETL run log.

A rolling rebuild window may be appropriate when source bookings can be modified after their original booking date.

---

## Reporting Views

BI and reporting platforms should reference views rather than raw tables whenever practical.

Views provide:

- Stable object names
- Controlled column names and data types
- Centralized business filters
- Consistent definitions across reports
- A compatibility layer when physical tables are renamed or reorganized
- Restricted exposure of internal or sensitive columns

Example:

```sql
CREATE OR ALTER VIEW report.vw_Bookings
AS
SELECT
    BookingID,
    LogicalID,
    RepositoryID,
    BookingDate,
    MarketKey,
    CompanyID,
    AccountID,
    BookingStatus,
    IsCompleted,
    RevenueAmount,
    LastModifiedUtc
FROM rpt.Booking
WHERE IsReportable = 1;
GO
```

### View Design Guidelines

- Give each column an explicit name.
- Avoid `SELECT *`.
- Keep report-facing data types stable.
- Document filters that remove test, duplicate, or nonreportable data.
- Put approved business definitions in one reusable layer.
- Do not hide expensive row-by-row logic inside many nested views.
- Index the underlying tables for the filters and joins used by reports.

---

## BI and Reporting Platforms

### BI Platforms

BI Platforms datasets or semantic models should connect to reporting views or dedicated summary views.

Recommended pattern:

```text
Database summary/detail tables
        |
        v
report views
        |
        v
BI semantic model
        |
        v
Reports and dashboards
```

Use the consolidated detail view when users require booking-level analysis. Use summary views when the required grain is already defined and the reduced row volume improves refresh and report performance.

### Reporting Platforms

Reporting Platforms datasets should also use report views or purpose-built stored procedures.

Use a stored procedure when a report requires parameter-driven processing that cannot be expressed efficiently through a reusable view. Keep business definitions aligned with the BI Platform view layer so the same metric does not produce conflicting results across tools.

---

## Validation and Reconciliation

Validation should occur before advancing the watermark.

### Schema Validation

Confirm that required source and target columns remain compatible.

Check for:

- Missing columns
- Added source columns
- Changed data types
- Changed lengths, precision, or scale
- Changed nullability
- Removed or renamed source objects

### Row-Level Validation

Recommended checks:

- Source keys missing from the target
- Target keys no longer represented by the source when deletion handling applies
- Duplicate target keys
- Multiple final records for one logical booking
- Invalid bridge relationships
- Null required identifiers
- Source records beyond the captured high-water mark accidentally included

### Count Validation

Record and compare:

- Extracted rows
- Staged rows
- Inserted rows
- Updated rows
- Rejected rows
- Target rows in the processed range
- Summary totals against consolidated detail totals

Counts should be interpreted with the procedure's insert, update, and retention behavior. Source and target totals are not necessarily expected to match when the target stores only selected records or additional history.

### Business Validation

Examples:

- Completed bookings do not exceed entered bookings for the same approved grain unless definitions allow it.
- Summary values tie back to the corresponding detail view.
- Reportable bookings use valid market and company mappings.
- Final booking selection is unique per logical booking.
- Revenue values use the approved booking state and source columns.

---

## Error Handling and Recovery

Each stored procedure should:

- Use `TRY...CATCH`.
- Roll back its active transaction when required.
- Record the failed run and step.
- Preserve the starting and attempted ending watermark.
- Include enough key information to identify failed rows.
- Rethrow critical errors to the parent procedure and SQL Server Agent.

Recovery should normally replay the same watermark range. Because merges and summary refreshes are idempotent, rerunning the failed range should not create duplicate records.

Do not manually move the watermark forward to bypass a failed row. Quarantine the invalid record or correct the transformation while preserving evidence of the failure.

---

## Indexing Considerations

Typical indexing candidates include:

### Raw Tables

- Source primary key
- Source modified timestamp or watermark column
- Logical booking ID
- Booking ID
- Archive timestamp

### Consolidated Booking Tables

- Reporting booking key
- Logical booking ID
- Booking date
- Market key
- Company ID
- Account ID
- Status or final-state indicator
- Last modified timestamp

### Summary Tables

- Summary grain columns
- Date
- Repository or market
- Common report filter combinations

Review actual SQL Server execution plans and Query Store data before adding overlapping indexes. Every index improves some reads but adds storage and write cost to the nightly pipeline.

---

## Security

Recommended access pattern:

- ETL service account: write access to staging, raw, reporting, and administration objects required by the pipeline.
- BI service account: read access to approved report views.
- Reporting Platforms service account: read or execute access to approved reporting objects.
- Analysts: read access to appropriate reporting views.
- Database administrators: administrative access controlled through existing policy.

Do not grant report users direct modification rights to ETL, watermark, raw, or summary tables.

---

## Deployment Order

Deploy database objects in dependency order:

```text
1. Database
2. Schemas
3. Raw/source-mirror tables
4. Staging tables
5. Administration and watermark tables
6. Reporting detail and bridge tables
7. Summary tables
8. Keys, constraints, and indexes
9. ETL helper procedures
10. Source load procedures
11. Consolidation procedures
12. Summary procedures
13. Validation procedures
14. Parent nightly procedure
15. Reporting views
16. Permissions
17. SQL Server Agent job
```

All scripts should be stored in source control and written to be repeatable where practical.

---

## Suggested Repository Structure

```text
booking-repository-database/
├── README.md
├── database/
│   ├── 001_create_database.sql
│   ├── 002_create_schemas.sql
│   └── 003_permissions.sql
├── tables/
│   ├── src/
│   ├── stg/
│   ├── rpt/
│   └── adm/
├── procedures/
│   ├── extract/
│   ├── merge/
│   ├── transform/
│   ├── summarize/
│   ├── validate/
│   └── orchestrate/
├── views/
│   └── report/
├── indexes/
├── jobs/
│   └── nightly_booking_pipeline.sql
├── validation/
│   ├── row_counts.sql
│   ├── missing_records.sql
│   ├── duplicate_records.sql
│   ├── booking_state_validation.sql
│   └── summary_reconciliation.sql
└── docs/
    ├── source_inventory.md
    ├── data_dictionary.md
    ├── pipeline_runbook.md
    └── recovery_procedure.md
```

---

## Operational Runbook

### Normal Nightly Run

```text
1. Start run log.
2. Read committed watermark.
3. Capture source high-water mark.
4. Stage changed source records.
5. Merge raw target tables.
6. Rebuild affected consolidated bookings.
7. Refresh affected summaries.
8. Execute validation checks.
9. Commit watermark.
10. Complete run log.
```

### Failed Run

```text
1. Review SQL Server Agent job history.
2. Identify the failed ETL run and step.
3. Review the stored starting and pending watermarks.
4. Correct the data, connection, capacity, or procedure issue.
5. Replay the uncommitted range.
6. Run row-level and summary validation.
7. Confirm that the committed watermark advanced only after success.
```

### Source Schema Change

```text
1. Detect and document the change.
2. Evaluate downstream table, procedure, view, BI, and Reporting Platforms impact.
3. Update development scripts.
4. Backfill or convert affected data if required.
5. Validate the target schema and pipeline.
6. Deploy the change in dependency order.
7. Confirm report compatibility.
```

---

## Definition of a Successful Pipeline Run

A nightly run is successful only when:

- The source range was captured.
- Expected source changes were extracted.
- Raw tables were loaded without unresolved critical errors.
- Consolidated booking records were refreshed.
- Impacted reporting summaries were refreshed.
- Required validations passed.
- The committed watermark was advanced to the captured high-water mark.
- The run log was marked successful.
- Reporting views remained queryable by BI and Reporting Platforms.

---

## Summary

The Booking Repository Reporting Database creates a repeatable SQL Server pattern for copying the required schema and data from an operational booking repository into a local reporting environment.

The design consists of:

- Source-compatible raw tables
- Staging tables for controlled processing
- Nightly stored procedure pipelines
- An `ETL_Watermark` table for incremental execution state
- Run, step, and error logging
- Consolidated booking and bridge tables
- Precalculated reporting summaries
- Stable views for BI and Reporting Platforms
- Validation and reconciliation before watermark advancement

The most important design rule is:

> The reporting database should expose stable, validated views while the ETL layer remains free to evolve underneath them.
