## About Me

Data Specialist with 6+ years of experience designing SQL Server data architectures, building ETL pipelines, and integrating multi-system operational data across 25+ markets. I focus on creating reliable data infrastructure that connects operational systems, automates complex workflows, and delivers decision-ready datasets for reporting and analytics.

## Featured Projects

### [Booking Repository ETL & Reporting Architecture](./Projects/booking-repository/Booking Repository Reporting.md)

Designed a SQL Server reporting repository that mirrors required structures from an operational booking system and uses nightly stored procedures to incrementally pipeline data into local tables. The solution uses ETL watermarks, execution logging, data validation, consolidated booking tables, and reporting views to provide reliable datasets for Power BI and SSRS while isolating reports from changes to the underlying pipeline.

### [Driver Assignment Integration Pipeline](./Projects/driver-assignment/Driver Assignment Pipeline.md)

Built a multi-system integration pipeline that retrieves driver and vehicle data from safety and booking platforms, cross-references records through stable internal keys, and combines booking-system shift activity into a unified assignment dataset. The pipeline manages driver creation and deactivation before synchronizing driver-to-vehicle assignments, with safeguards for unmatched records, stale assignments, duplicate relationships, and incomplete assignment end times.
