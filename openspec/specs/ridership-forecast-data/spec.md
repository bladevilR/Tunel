# ridership-forecast-data Specification

## Purpose
TBD - created by archiving change ingest-ridership-forecast-xls. Update Purpose after archive.
## Requirements
### Requirement: Forecast ridership ingestion
The system SHALL ingest the 0528 existing-line forecast workbook into a normalized forecast ridership dataset without replacing observed monthly ridership data.

#### Scenario: Parse line forecast sheets
- **WHEN** the ingestion process reads `0528既有线路客流预测数据.xls`
- **THEN** it creates forecast records for each supported line sheet, station, horizon year, direction, boarding count, and alighting count

#### Scenario: Preserve observed ridership
- **WHEN** forecast records are generated
- **THEN** existing `ridership.json` observed monthly inbound records remain available and distinguishable from forecast records

### Requirement: Forecast station context
The system SHALL expose forecast ridership through station context lookup using station aliases and line information.

#### Scenario: Selected station has forecast data
- **WHEN** a user selects a station with 2032 or 2047 forecast records
- **THEN** the station context response includes observed ridership, forecast ridership rollups, source workbook name, and horizon-year labels

#### Scenario: Station name is ambiguous across lines
- **WHEN** a station name matches multiple forecast line records and the project line is unknown
- **THEN** the system returns all matching forecast records with line labels instead of silently selecting one

### Requirement: Forecast evidence in reports
Generated reports SHALL cite forecast ridership as future-horizon evidence when available and SHALL not present it as current measured ridership.

#### Scenario: Report includes forecast evidence
- **WHEN** report export runs for a station with forecast records
- **THEN** the report includes a concise current-vs-forecast客流 statement with source, horizon year, and directional context

#### Scenario: Forecast data is unavailable
- **WHEN** a selected station has no forecast record
- **THEN** the report keeps the forecast dimension as a data gap or follow-up check and continues using observed ridership if present

