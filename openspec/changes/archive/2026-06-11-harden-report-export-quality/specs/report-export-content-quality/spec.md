## MODIFIED Requirements

### Requirement: Reliable report export
The report export workflow SHALL generate export artifacts through the backend, return downloadable file metadata for each generated file, and make user-visible browser download behavior verifiable.

#### Scenario: Export formal report
- **WHEN** a user clicks report export after entering or saving a project
- **THEN** the backend generates the mandatory DOCX report and evidence snapshot artifacts, and the frontend displays served download links for each artifact

#### Scenario: Export history updates
- **WHEN** a report export succeeds
- **THEN** the export history endpoint and frontend export-history list include the newly generated artifacts

#### Scenario: Export failure is visible
- **WHEN** report generation fails or a configured export runtime is missing
- **THEN** the frontend displays the backend error message, identifies the failed artifact class, and does not pretend that files were generated

#### Scenario: Browser download link is usable
- **WHEN** a generated report link is shown in the frontend
- **THEN** opening the link through the browser returns the artifact with a valid content type, non-zero size, and no absolute filesystem-only path

### Requirement: Legacy report format alignment
The generated formal report SHALL follow the selected legacy reference structure for section order, title hierarchy, major content blocks, and readable DOCX organization.

#### Scenario: Validate section order
- **WHEN** a formal report is generated
- **THEN** its top-level sections match the agreed legacy reference order or an explicit mapping documented in the implementation

#### Scenario: Validate heading and block hierarchy
- **WHEN** a formal report DOCX is generated
- **THEN** it contains a readable heading hierarchy, separates evaluation facts from recommendations and risks, and avoids collapsing required content into one undifferentiated narrative block

#### Scenario: Required sections are substantive
- **WHEN** a formal report is generated
- **THEN** project facts, evaluation basis, station context, scoring, recommendation, risks, data gaps, and implementation suggestions are non-empty and source-aware

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

#### Scenario: Evidence source is unavailable
- **WHEN** the system lacks authoritative data for a protection, safety, or planning claim
- **THEN** the report labels that item as pending manual verification and does not cite fabricated document names, article numbers, or conclusions
