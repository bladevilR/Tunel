## Purpose
Define local-first platform readiness contracts for deferred integrations, migration settings, identity, generated-image placeholders, and shared administrator data.

## Requirements

### Requirement: Feature-flagged platform readiness
Platform-readiness features SHALL be represented by explicit configuration or feature flags so unfinished integrations do not appear as fully available user functionality.

#### Scenario: Integration is disabled
- **WHEN** generated-image, account, or deployment-integration functionality is not configured
- **THEN** the UI and API expose a clear disabled or placeholder state rather than a broken action

### Requirement: Generated-image API placeholder
The system SHALL define a stable placeholder contract for future generated-image API integration without requiring the API for local schematic export.

#### Scenario: Request image generation while disabled
- **WHEN** image generation is requested but no provider is configured
- **THEN** the system returns a structured "not configured" response and leaves existing schematic export behavior unaffected

### Requirement: Account identity contract
The system SHALL reserve a minimal user identity model for later account support without making anonymous local usage impossible.

#### Scenario: Local anonymous usage
- **WHEN** no account system is configured
- **THEN** users can still create, save, import, export, and report on local projects under a local anonymous identity

### Requirement: Server migration readiness
The system SHALL document and expose the deployment settings needed to move the local MVP to a server environment.

#### Scenario: Review migration readiness
- **WHEN** an operator prepares a server deployment
- **THEN** documentation or configuration identifies host, port, data paths, export paths, runtime dependencies, and secret/API-key requirements

### Requirement: Administrator data management boundary
The system SHALL distinguish administrator-maintained shared data such as station outlines from user project data.

#### Scenario: Apply shared data to a project
- **WHEN** a shared station outline is applied to a user project
- **THEN** the project stores a reference or copied snapshot with source metadata so later shared-data edits do not silently change past project outputs
