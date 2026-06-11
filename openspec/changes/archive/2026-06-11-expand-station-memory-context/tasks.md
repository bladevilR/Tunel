## 1. Station Memory Model

- [x] 1.1 Define the station-memory JSON schema with identity, aliases, context values, schematic assets, notes, version, and provenance fields.
- [x] 1.2 Add load/save helpers and validation for station-memory records.
- [x] 1.3 Migrate or map existing administrator station outlines into the new memory model without losing current apply behavior.

## 2. API And UI Flows

- [x] 2.1 Add backend endpoints or actions for listing, saving, and applying station memory records.
- [x] 2.2 Update station search/context responses to include memory-backed matches and source labels.
- [x] 2.3 Add frontend controls for saving corrections to memory and applying remembered station data to a project/schematic.

## 3. Provenance And Verification

- [x] 3.1 Store memory application snapshots in project records with source version metadata.
- [x] 3.2 Verify manual overrides are preserved unless the user explicitly applies memory values.
- [x] 3.3 Add tests for alias search, memory save/apply, outline reuse, and project snapshot immutability.
