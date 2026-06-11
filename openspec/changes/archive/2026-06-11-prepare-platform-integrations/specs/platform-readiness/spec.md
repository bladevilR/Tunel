## MODIFIED Requirements

### Requirement: Generated-image API placeholder
The system SHALL define a stable generated-image API contract that supports both a disabled placeholder state and a configured provider state without affecting local schematic PNG export.

#### Scenario: Request image generation while disabled
- **WHEN** image generation is requested but no provider is configured
- **THEN** the system returns a structured "not configured" response and leaves existing schematic export behavior unaffected

#### Scenario: Request image generation while enabled
- **WHEN** a generated-image provider is configured and a valid image-generation request is submitted
- **THEN** the system creates a served image artifact, records provider/source metadata, and returns downloadable file metadata consistent with other export artifacts

#### Scenario: Provider failure is visible
- **WHEN** the configured generated-image provider fails
- **THEN** the API returns a structured error that does not remove or overwrite existing schematic PNG artifacts

### Requirement: Account identity contract
The system SHALL support local anonymous usage and a minimal account/owner model for later server deployment.

#### Scenario: Local anonymous usage
- **WHEN** no account system is configured
- **THEN** users can still create, save, import, export, and report on local projects under a local anonymous identity

#### Scenario: Account mode enabled
- **WHEN** account mode is enabled
- **THEN** saved projects, station-memory edits, exports, and generated images include owner metadata linked to the active account or local user record

#### Scenario: Migrate anonymous project ownership
- **WHEN** a local anonymous project is associated with an account
- **THEN** the project keeps its stable ID and history while recording the ownership migration metadata

### Requirement: Server migration readiness
The system SHALL document, expose, and validate the deployment settings needed to move the local MVP to a server environment.

#### Scenario: Review migration readiness
- **WHEN** an operator prepares a server deployment
- **THEN** documentation or configuration identifies host, port, data paths, export paths, runtime dependencies, and secret/API-key requirements

#### Scenario: Validate server configuration
- **WHEN** the server migration validation runs
- **THEN** it checks required directories, writable export paths, API-key/capability consistency, account mode, and generated-image provider settings before declaring readiness

#### Scenario: Capability status matches config
- **WHEN** deployment configuration changes generated-image, account, or export settings
- **THEN** `/api/capabilities` and the frontend status display reflect the actual enabled/disabled state
