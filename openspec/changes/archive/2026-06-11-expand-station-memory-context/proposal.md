## Why

Feedback asks for station memory, better station storage, station search, station type preselection, and global administrator station outlines. The previous implementation added search and a minimal shared outline boundary, but station memory is still too shallow for repeated station studies and does not give operators a clear way to save, reuse, or provenance-track station-level corrections.

## What Changes

- Expand station memory into reusable station records containing aliases, station type overrides, common context notes, schematic outlines, exits, and source metadata.
- Allow project-derived station corrections to be saved back to station memory with explicit operator intent.
- Make station search and autofill prefer memory records while preserving source labels and manual override status.
- Ensure applying station memory snapshots to projects does not silently mutate historical project outputs.
- Add verification for station memory save/apply/search behavior.

## Capabilities

### New Capabilities

### Modified Capabilities

- `project-intake-station-context`: Expand station memory and reusable station-context requirements beyond one-off search/autofill.

## Impact

- Backend station context APIs and shared station data storage.
- Frontend station search, station context cards, and project intake save/apply flows.
- Schematic station outline application.
- Data provenance in saved project records and reports.
