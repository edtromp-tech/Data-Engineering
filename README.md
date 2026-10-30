## About Me

Data Specialist with 6+ years of experience designing SQL Server data architectures, building ETL pipelines, and integrating multi-system operational data across 25+ markets. I focus on creating reliable data infrastructure that connects operational systems, automates complex workflows, and delivers decision-ready datasets for reporting and analytics.

See what I have been up to with my [projects](./Projects) and [continuous learning](./Continuous%20Learning.md)

## Featured Projects

### [Booking Repository ETL & Reporting Architecture](./Projects/booking-repository/Booking%20Repository%20Reporting%20Database.md)

Designed a SQL Server reporting repository that mirrors required structures from an operational booking system and uses nightly stored procedures to incrementally pipeline data into local tables. The solution uses ETL watermarks, execution logging, data validation, consolidated booking tables, and reporting views to provide reliable datasets for Power BI and SSRS while isolating reports from changes to the underlying pipeline.

### [Driver Assignment Integration Pipeline](./Projects/driver-assignment/Driver%20Assignment%20Pipeline.md)

Built a multi-system integration pipeline that retrieves driver and vehicle data from safety and booking platforms, cross-references records through stable internal keys, and combines booking-system shift activity into a unified assignment dataset. The pipeline manages driver creation and deactivation before synchronizing driver-to-vehicle assignments, with safeguards for unmatched records, stale assignments, duplicate relationships, and incomplete assignment end times.

### [Dynamic Table Merge ETL](./Projects/sp_Merge_RemoteTable/sp_Merge_RemoteTable.md)
This project demonstrates a reusable, metadata-driven ETL framework built in SQL Server for synchronizing tables between remote and local databases.
Instead of maintaining a separate stored procedure for every table or database, the process dynamically determines the source and target configuration, discovers table columns from SQL Server metadata, generates the required SQL statements, and performs incremental inserts and updates.
The goal is to reduce duplicated ETL code while making the pipeline easier to maintain as database schemas evolve.

### [Credit Card Transaction Data](./Projects/fraud_detection/README.md)
A small, tested pipeline that ingests credit-card transaction CSVs, repairs what can be repaired deterministically, quarantines what can't, and loads the rest into a warehouse table without ever creating duplicates on re-runs. Most portfolio ETL projects load a tidy CSV into a table. This one starts from the assumption that source data is wrong and shows what you do about it.

