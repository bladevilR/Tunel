## 1. Generated Image Integration

- [x] 1.1 Define generated-image request/response payloads for disabled, success, and provider-failure states.
- [x] 1.2 Implement a provider abstraction and configured-provider path that saves served image artifacts with metadata.
- [x] 1.3 Update frontend capability display and image-generation action states.

## 2. Account And Ownership

- [x] 2.1 Add minimal account/local-user records and owner metadata for projects, station-memory edits, exports, and generated images.
- [x] 2.2 Preserve anonymous local usage when account mode is disabled.
- [x] 2.3 Add an ownership migration path from anonymous records to account-owned records.

## 3. Server Migration

- [x] 3.1 Centralize server configuration for host, port, data paths, export paths, secrets, account mode, and generated-image settings.
- [x] 3.2 Add deployment validation checks and update `/api/capabilities` to reflect resolved configuration.
- [x] 3.3 Update deployment docs and verification scripts for server-mode startup and capability status.
