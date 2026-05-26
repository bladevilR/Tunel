## Purpose
Define project intake portability, station lookup, station-context autofill, and reusable station-level records for repeated station and parcel studies.

## Requirements

### Requirement: Project intake import and export
The system SHALL allow users to export and import project intake data as versioned JSON without requiring generated report files.

#### Scenario: Export current project intake
- **WHEN** a user chooses to export the current project intake page
- **THEN** the system downloads a JSON file containing project fields, research options, linked schematic metadata, schema version, and timestamps

#### Scenario: Import project intake
- **WHEN** a user imports a valid project intake JSON file
- **THEN** the form is populated, the project can be saved under its imported or edited name, and validation errors are shown for missing or incompatible fields

### Requirement: Custom project naming
The system SHALL preserve user-provided project names independently from generated IDs and project codes.

#### Scenario: Save a named project
- **WHEN** a user enters a custom project name and saves the project
- **THEN** the project list, project selector, report title fallback, and export slug use that name where appropriate without losing the stable record ID

### Requirement: Station search
The system SHALL provide station search suggestions backed by existing station, ridership, operations, amenities, and station-index data.

#### Scenario: Search by station alias
- **WHEN** a user types a station name or known alias into the station search field
- **THEN** the system returns ranked station suggestions with source labels and enough context for the user to choose the correct station

### Requirement: Station context autofill
The system SHALL autofill station-related fields from the selected station context while allowing manual override.

#### Scenario: Select a station suggestion
- **WHEN** a user selects a station from search results
- **THEN** the form preselects available line, TOD/location level, daily inbound value, nearby exit/context summaries, and station type when those values are known

#### Scenario: Preserve manual override
- **WHEN** a user manually changes an autofilled station field
- **THEN** the system preserves the manual value and records that the value came from user input rather than automatic station context

### Requirement: Station type inference
The system SHALL infer station type from existing station data or line count when the user has not manually selected a station type.

#### Scenario: Multiple lines imply transfer station
- **WHEN** selected station data indicates more than one line or a transfer marker
- **THEN** station type is preselected as a transfer type unless the user has already manually chosen another value

#### Scenario: Single known line implies normal station
- **WHEN** selected station data indicates one line and no transfer marker
- **THEN** station type is preselected as a normal station unless the user has already manually chosen another value

### Requirement: Station memory and administrator outlines
The system SHALL support reusable station-level records for station outlines and commonly used station context without coupling them to one project.

#### Scenario: Reuse administrator station outline
- **WHEN** an administrator-maintained station outline exists for the selected station
- **THEN** a user can apply that outline to a schematic project without redrawing it from scratch
