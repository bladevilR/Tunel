## MODIFIED Requirements

### Requirement: Station memory and administrator outlines
The system SHALL support reusable station-level records for station aliases, station type/context corrections, common station notes, station outlines, exits, and schematic assets without coupling them to one project.

#### Scenario: Reuse administrator station outline
- **WHEN** an administrator-maintained station outline exists for the selected station
- **THEN** a user can apply that outline to a schematic project without redrawing it from scratch

#### Scenario: Save station correction to memory
- **WHEN** an operator edits station type, aliases, common notes, exits, or reusable outlines and chooses to save them as station memory
- **THEN** the system stores a versioned station-memory record with source metadata and does not overwrite unrelated project-specific fields

#### Scenario: Apply memory snapshot to project
- **WHEN** a user applies a station-memory record to a project
- **THEN** the project stores a copied snapshot or source reference with memory version and applied timestamp, so later memory edits do not silently change past project outputs

#### Scenario: Search uses station memory
- **WHEN** a user searches by a station alias or remembered display name
- **THEN** station suggestions include memory-backed matches with source labels alongside official station, ridership, operations, and amenities sources

#### Scenario: Preserve manual override against memory
- **WHEN** station memory provides a value but the project already has a user-edited override
- **THEN** the system keeps the user value unless the user explicitly applies the memory value
