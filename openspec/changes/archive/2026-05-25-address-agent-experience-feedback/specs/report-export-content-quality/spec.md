## ADDED Requirements

### Requirement: Reliable report export
The report export workflow SHALL generate export artifacts through the backend and return downloadable file metadata for each generated file.

#### Scenario: Export formal report
- **WHEN** a user clicks report export after entering or saving a project
- **THEN** the backend generates the expected report artifacts and the frontend displays served download links for each artifact

#### Scenario: Export history updates
- **WHEN** a report export succeeds
- **THEN** the export history endpoint and frontend export-history list include the newly generated artifacts

#### Scenario: Export failure is visible
- **WHEN** report generation fails
- **THEN** the frontend displays the backend error message and does not pretend that files were generated

### Requirement: Legacy report format alignment
The generated formal report SHALL follow the selected legacy reference structure for section order, title hierarchy, and major content blocks.

#### Scenario: Validate section order
- **WHEN** a formal report is generated
- **THEN** its top-level sections match the agreed legacy reference order or an explicit mapping documented in the implementation

### Requirement: Report content hierarchy
The generated report SHALL separate project facts, evaluation basis, station context, scoring, scheme recommendation, risks, data gaps, and implementation suggestions into distinct readable sections.

#### Scenario: Generate readable hierarchy
- **WHEN** a report is exported for a complete or partially complete project
- **THEN** the report contains clear section headings and does not collapse all evaluation material into one undifferentiated narrative block

### Requirement: Additional evidence dimensions
The report SHALL include ridership, old-city protection, safety, and rail-protection content when data or applicable rules are available, and SHALL mark unavailable dimensions as follow-up checks rather than facts.

#### Scenario: Ridership data exists
- **WHEN** station ridership data is available for the selected station
- **THEN** the report includes the ridership value, source, and how it affects the interconnection judgement

#### Scenario: Old-city protection data is missing
- **WHEN** the project may need old-city protection consideration but no authoritative source is available in the workspace
- **THEN** the report flags old-city protection as a manual verification item instead of inventing a conclusion

#### Scenario: Rail-protection notice is appended
- **WHEN** a formal report is generated
- **THEN** the report includes a safety and rail-protection requirements notice near the end or in an appendix

### Requirement: Export verification
The implementation SHALL include automated or scripted verification for report export, file serving, and exported metadata.

#### Scenario: Run export verification
- **WHEN** the report export verification script runs against a sample project
- **THEN** it confirms generated files exist, are non-empty, are listed by `/api/exports`, and have browser-downloadable URLs
