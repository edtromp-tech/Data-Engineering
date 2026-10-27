# Metadata-Driven SQL Server ETL Merge

## Overview

This project demonstrates a reusable, metadata-driven ETL framework built in SQL Server for synchronizing tables between remote and local databases.

Instead of maintaining a separate stored procedure for every table or database, the process dynamically determines the source and target configuration, discovers table columns from SQL Server metadata, generates the required SQL statements, and performs incremental inserts and updates.

The goal is to reduce duplicated ETL code while making the pipeline easier to maintain as database schemas evolve.

## Key Features

- **Metadata-driven column discovery**
  - Reads column information directly from SQL Server system catalog views.
  - Dynamically generates `SELECT`, `INSERT`, `VALUES`, and `UPDATE` column lists.
  - Reduces the need to modify ETL procedures when columns are added to supported tables.

- **Dynamic source and target configuration**
  - Resolves linked servers, source databases, and target databases from a configuration table.
  - Allows the same stored procedure to support multiple database instances.

- **Incremental data loading**
  - Uses a `modified` timestamp, or another configurable watermark column, to retrieve only new or changed records.
  - Avoids repeatedly processing an entire source table during normal ETL execution.

- **Watermark management**
  - Maintains the most recently processed modification timestamp for each table.
  - Automatically creates the watermark record when one does not already exist.
  - Allows an initial look-back period to be configured for newly initialized tables.

- **Dynamic upsert processing**
  - Uses SQL Server `MERGE` logic to update existing records and insert new records.
  - Supports configurable key columns rather than requiring table-specific merge procedures.

- **Schema-aware processing**
  - Excludes identity, computed, `timestamp`, and `rowversion` columns from dynamically generated write operations where appropriate.
  - Uses SQL Server metadata such as `sys.columns`, `sys.tables`, `sys.schemas`, and `sys.types`.

- **Error handling**
  - Uses `TRY...CATCH`, `THROW`, and `XACT_ABORT` to surface ETL failures to the calling process.
  - Designed so failed executions can be detected by scheduling and orchestration systems such as SQL Server Agent.

- **Debugging support**
  - Optional debug output exposes the dynamically generated SQL, column mappings, source/target configuration, and watermark information.
  - Useful for validating generated statements without maintaining table-specific SQL.

## Architecture

The general processing flow is:

1. Receive the source instance and table name.
2. Retrieve source and target information from the configuration table.
3. Query the target database metadata to discover eligible columns.
4. Dynamically generate the required column mappings.
5. Retrieve the previous ETL watermark.
6. Query the remote source for records at or beyond that watermark.
7. Merge the changed records into the target table.
8. Determine the newest successfully processed watermark.
9. Update or create the table's watermark record.
10. Surface any processing errors to the calling application or SQL Server Agent job.

## Example Usage

```sql
EXEC [etl].[sp_Merge_RemoteTable]
     @SourceInstance   = 'Source01',
     @TableName        = 'SampleTransactions'
```


                    Source Configuration
                            |
                            v
                 sp_Merge_RemoteTable
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        Table Metadata   Watermark    Source Data
              |             |             |
              +-------------+-------------+
                            |
                            v
                     Dynamic MERGE
                            |
                            v
                      Target Table
