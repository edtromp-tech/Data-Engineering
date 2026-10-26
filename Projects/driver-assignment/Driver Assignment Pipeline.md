# Driver Assignment Pipeline

## Overview

The Driver Assignment Pipeline synchronizes driver and vehicle information between the **booking system** and the **safety system**.

The pipeline retrieves vehicles and drivers from the safety system, retrieves vehicles, drivers, and driver shifts from the booking system, cross-references those records through internal matching keys, and builds a consolidated assignment table. The resulting data is then used to create, update, activate, deactivate, and assign drivers in the safety system.

The processing order is important:

1. Create or update driver profiles.
2. Deactivate drivers who are no longer active.
3. Build the current driver-to-vehicle assignment set.
4. Apply driver assignments in the safety system.
5. Close or replace assignments that are no longer valid.

Driver lifecycle updates must finish before vehicle assignments are submitted so that assignments reference the correct active driver records.

---

## Pipeline Architecture

```text
Safety System                              Booking System
--------------                             --------------
Vehicles                                   Vehicles
Drivers                                    Drivers
                                           Driver Shifts
     |                                          |
     +-------------------+----------------------+
                         |
                         v
                Staging / Normalization
                         |
                         v
                 Cross-Reference Keys
                         |
                         v
              Consolidated Assignment Table
                         |
          +--------------+--------------+
          |                             |
          v                             v
 Driver Lifecycle Updates        Assignment Updates
 Create / Update Drivers         Assign Driver to Vehicle
 Activate / Deactivate           End Stale Assignments
```

---

## Source Data

### Safety System

The pipeline retrieves the current safety-system records used to determine whether an entity already exists and whether an update is required.

#### Vehicles

Recommended fields:

- Safety vehicle ID
- Vehicle name or number
- VIN
- License plate
- Active status
- Existing assigned driver, when available
- Existing assignment start and end timestamps, when available

#### Drivers

Recommended fields:

- Safety driver ID
- Driver name
- Employee or driver number
- Username or email, when available
- Active status
- External or internal reference key

### Booking System

The booking system provides the operational source data used to determine which drivers and vehicles are active and which driver is associated with each vehicle.

#### Vehicles

Recommended fields:

- Booking-system vehicle ID
- Vehicle number or callsign
- VIN
- License plate
- Fleet or location
- Active status

#### Drivers

Recommended fields:

- Booking-system driver ID
- Stable driver key
- Driver number
- Driver name
- Active status
- Fleet or location

#### Driver Shifts

Recommended fields:

- Shift ID
- Driver ID or driver key
- Vehicle ID
- Shift start timestamp
- Shift end timestamp
- Shift status
- Fleet or location

Driver shifts represent the operational relationship used to determine the current driver-to-vehicle assignment.

---

## Processing Stages

### 1. Extract Source Records

Retrieve the required records from both systems.

```text
Safety System:
- Vehicles
- Drivers

Booking System:
- Vehicles
- Drivers
- Driver shifts
```

Each extraction should record:

- Pipeline run ID
- Source system
- Extraction timestamp
- Record count
- Success or failure status
- Error details, when applicable

### 2. Stage and Normalize

Load source records into staging tables before matching them.

Normalization should include, where applicable:

- Trimming leading and trailing spaces
- Standardizing casing
- Removing formatting from driver and vehicle numbers
- Normalizing VINs and license plates
- Converting blank strings to `NULL`
- Converting timestamps to a consistent time zone
- Standardizing active and inactive status values
- Deduplicating source records

Do not use names as the primary long-term identifier when a stable system key is available. Names should be treated as fallback matching attributes because they may be changed or shared.

### 3. Cross-Reference Drivers

Create or maintain a driver cross-reference table that links each booking-system driver to the corresponding safety-system driver.

Example structure:

| Column | Description |
|---|---|
| `DriverCrossReferenceID` | Internal surrogate key |
| `BookingDriverID` | Driver identifier from the booking system |
| `BookingDriverKey` | Stable booking-system driver key |
| `SafetyDriverID` | Driver identifier from the safety system |
| `MatchMethod` | Key, driver number, name, or manual override |
| `MatchStatus` | Matched, unmatched, ambiguous, or excluded |
| `FirstMatchedAt` | First successful match timestamp |
| `LastValidatedAt` | Most recent validation timestamp |
| `IsManualOverride` | Indicates a manually maintained match |

Recommended matching priority:

1. Existing approved cross-reference
2. Stable booking-system driver key
3. Employee or driver number
4. Normalized username or email
5. Normalized driver name as a controlled fallback
6. Manual review when no unique match is available

A name-based match should only be accepted when it produces exactly one valid candidate.

### 4. Cross-Reference Vehicles

Create or maintain a vehicle cross-reference table that links booking-system vehicles to safety-system vehicles.

Example structure:

| Column | Description |
|---|---|
| `VehicleCrossReferenceID` | Internal surrogate key |
| `BookingVehicleID` | Vehicle identifier from the booking system |
| `SafetyVehicleID` | Vehicle identifier from the safety system |
| `VIN` | Vehicle identification number |
| `VehicleNumber` | Operational vehicle number or callsign |
| `MatchMethod` | VIN, vehicle number, license plate, or manual override |
| `MatchStatus` | Matched, unmatched, ambiguous, or excluded |
| `LastValidatedAt` | Most recent validation timestamp |

Recommended matching priority:

1. Existing approved cross-reference
2. VIN
3. Stable vehicle number or callsign within the same fleet or location
4. License plate within the same fleet or location
5. Manual review

### 5. Synchronize Driver Lifecycle

Driver lifecycle processing must occur before driver assignments.

#### Create or Update Drivers

For each active booking-system driver:

- Create the driver in the safety system if no safety driver exists.
- Update the safety driver when controlled profile attributes have changed.
- Preserve the returned safety driver ID in the driver cross-reference table.
- Activate the safety driver if the source indicates the driver is active and activation is permitted by the business rules.

#### Deactivate Drivers

For each driver who should no longer be active:

- End any open vehicle assignment associated with the driver.
- Deactivate the driver in the safety system.
- Record the deactivation result and timestamp.
- Do not create a new assignment for the driver during the same run.

Deactivation rules should be based on an authoritative status from the booking or source system, not merely the absence of a driver from one extraction.

### 6. Build the Consolidated Assignment Table

Join the booking-system driver shifts to the driver and vehicle cross-reference tables.

Example structure:

| Column | Description |
|---|---|
| `AssignmentID` | Internal assignment identifier |
| `PipelineRunID` | Run that produced the record |
| `BookingShiftID` | Source shift identifier |
| `BookingDriverID` | Booking-system driver identifier |
| `SafetyDriverID` | Safety-system driver identifier |
| `BookingVehicleID` | Booking-system vehicle identifier |
| `SafetyVehicleID` | Safety-system vehicle identifier |
| `ShiftStartUTC` | Assignment start timestamp |
| `ShiftEndUTC` | Assignment end timestamp |
| `AssignmentStatus` | Pending, assigned, ended, skipped, or failed |
| `MatchStatus` | Valid, unmatched driver, unmatched vehicle, or ambiguous |
| `ProcessedAt` | Processing timestamp |
| `ErrorMessage` | Failure reason, when applicable |

Only rows with a valid driver match, valid vehicle match, valid shift range, and active driver should be eligible for assignment.

### 7. Resolve Current Assignments

Before writing to the safety system, compare the desired assignment state with the current safety-system assignment state.

For each driver and vehicle pair, determine whether to:

- Create a new assignment
- Leave an identical active assignment unchanged
- End an obsolete assignment
- Replace an incorrect assignment
- Skip an invalid or ambiguous assignment

The pipeline should prevent:

- One driver being actively assigned to multiple vehicles unless explicitly allowed
- Multiple drivers being actively assigned to one vehicle unless explicitly allowed
- Assignments to inactive drivers
- Assignments to inactive or unmatched vehicles
- Overlapping assignments for the same driver or vehicle
- Open assignments without an appropriate end timestamp
- Re-creating an assignment that already exists

### 8. Apply Assignments in the Safety System

For each eligible consolidated assignment:

1. Confirm that the safety driver exists and is active.
2. Confirm that the safety vehicle exists and is eligible for assignment.
3. End any conflicting or stale assignment.
4. Create or update the desired assignment.
5. Store the safety-system response and assignment identifier.
6. Mark the consolidated record as assigned or failed.

Assignments should be processed idempotently. Re-running the pipeline with the same source state should not create duplicate driver profiles or duplicate assignments.

---

## Required Processing Order

```text
1. Extract source data
2. Normalize and stage source data
3. Match vehicles
4. Match drivers
5. Create missing drivers
6. Update existing drivers
7. End assignments for drivers being deactivated
8. Deactivate drivers
9. Revalidate active driver and vehicle keys
10. Build the desired assignment table
11. End stale or conflicting assignments
12. Create current assignments
13. Validate results
14. Log pipeline completion
```

This sequence prevents the pipeline from assigning a missing, inactive, or stale safety-system driver to a vehicle.

---

## Validation Rules

### Driver Validation

- Booking driver has a valid stable key.
- Driver cross-reference resolves to one safety driver.
- Safety driver exists after lifecycle synchronization.
- Driver is active before assignment.
- Driver is not marked for deactivation in the current run.

### Vehicle Validation

- Booking vehicle resolves to one safety vehicle.
- Vehicle is active or otherwise eligible.
- Vehicle match is not ambiguous.

### Shift Validation

- Shift has both a valid driver and vehicle.
- Shift start is present.
- Shift end is after shift start when an end exists.
- Shift is the selected current or authoritative shift.
- Duplicate shift records are removed.

### Assignment Validation

- No duplicate desired assignment exists.
- No unintended overlapping open assignment exists.
- Existing identical assignments are not recreated.
- Replaced or completed assignments receive an end timestamp.
- API responses are captured and checked before marking success.

---

## Exception Handling

Records that cannot be safely matched or assigned should be quarantined rather than guessed.

Suggested exception reasons:

- Driver not found
- Multiple driver matches
- Vehicle not found
- Multiple vehicle matches
- Missing driver key
- Missing vehicle key
- Driver inactive
- Vehicle inactive
- Invalid shift range
- Conflicting active assignment
- Safety-system API failure
- Rate limit or timeout
- Unexpected source-system status

Each exception record should include the pipeline run ID, source identifiers, exception type, original source values, and error message.

---

## Logging and Audit

Each run should maintain a pipeline-level log and row-level results.

### Pipeline Run Log

Recommended fields:

- `PipelineRunID`
- `PipelineName`
- `StartedAt`
- `CompletedAt`
- `Status`
- `DriversRead`
- `DriversCreated`
- `DriversUpdated`
- `DriversActivated`
- `DriversDeactivated`
- `VehiclesRead`
- `ShiftsRead`
- `AssignmentsCreated`
- `AssignmentsEnded`
- `AssignmentsSkipped`
- `AssignmentsFailed`
- `ErrorMessage`

### Assignment Audit Log

The audit log should preserve:

- Prior assignment state
- Desired assignment state
- Action attempted
- Request timestamp
- Response timestamp
- Result status
- External assignment ID
- Error response

Avoid logging access tokens, secrets, or unnecessary personal information.

---

## Idempotency and Recovery

The pipeline should be safe to rerun after a partial failure.

Recommended controls:

- Use stable source and cross-reference keys.
- Upsert driver and vehicle mappings.
- Compare desired assignments with existing assignments before writing.
- Store external identifiers returned by the safety system.
- Commit lifecycle and assignment results in recoverable batches.
- Retry transient API failures with bounded retries.
- Do not retry permanent validation errors automatically.
- Resume from the last successful stage or rebuild the desired state from source data.

---

## Security and Configuration

Store environment-specific values outside the application code.

Typical configuration values include:

- Safety-system API base URL
- Booking-system connection information
- Authentication secret references
- API timeout
- Retry limits
- Batch size
- Location or fleet mappings
- Active and inactive status mappings
- Logging level

Secrets should be stored in an approved secret-management service and must not be committed to source control.

---

## Monitoring

Recommended alerts:

- Pipeline failure
- Source extraction failure
- Unusual increase in unmatched drivers or vehicles
- Driver creation or deactivation failure
- Assignment failure
- Open assignments missing end timestamps
- Driver assigned to multiple vehicles
- Vehicle assigned to multiple active drivers
- No source records returned when records are normally expected

Recommended operational metrics:

- Match rate for drivers
- Match rate for vehicles
- Assignment success rate
- Number of open assignments
- Number of stale assignments ended
- Number of active drivers created or updated
- Number of drivers deactivated
- Number of quarantined records
- Pipeline duration by stage

---

## Suggested Repository Structure

```text
driver-assignment-pipeline/
├── README.md
├── config/
│   └── settings.example.json
├── src/
│   ├── booking_system/
│   │   ├── drivers.py
│   │   ├── vehicles.py
│   │   └── shifts.py
│   ├── safety_system/
│   │   ├── drivers.py
│   │   ├── vehicles.py
│   │   └── assignments.py
│   ├── matching/
│   │   ├── driver_matcher.py
│   │   └── vehicle_matcher.py
│   ├── pipeline/
│   │   ├── lifecycle.py
│   │   ├── assignments.py
│   │   └── orchestrator.py
│   └── logging/
│       └── audit.py
├── sql/
│   ├── staging/
│   ├── cross_reference/
│   ├── assignments/
│   └── validation/
└── tests/
    ├── test_driver_matching.py
    ├── test_vehicle_matching.py
    ├── test_driver_lifecycle.py
    └── test_assignments.py
```

---

## Summary

The Driver Assignment Pipeline creates a controlled bridge between booking-system operations and safety-system vehicle assignments.

Its main responsibilities are to:

- Retrieve driver and vehicle data from both systems.
- Retrieve driver shifts from the booking system.
- Maintain stable driver and vehicle cross-references.
- Create and update drivers in the safety system.
- End active assignments and deactivate drivers when required.
- Build a consolidated desired-assignment table.
- Assign active drivers to matched vehicles.
- Close stale or conflicting assignments.
- Log every lifecycle and assignment action for troubleshooting and audit.

The core design principle is that **driver identity and lifecycle state must be synchronized before assignments are applied**.
