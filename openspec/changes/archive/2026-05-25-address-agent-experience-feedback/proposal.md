## Why

The 2026-05-25 "智能体使用体验" feedback identifies blockers in the schematic drawing workflow, report export, project intake, and station data reuse. Addressing these issues now will turn the current MVP from a demo-oriented tool into a more reliable pilot workflow for repeated station and parcel studies.

## What Changes

- Make schematic PNG export produce an immediately downloadable local file/link instead of only exposing a server filesystem path.
- Improve schematic drawing ergonomics: live guide line while drawing, layer deletion, collapsible drawing panel, adjustable 3D map view, and clearer floor controls capped at 30 above-ground floors.
- Extend schematic geometry from single station/parcel/basement assumptions to support multiple parcels, multiple channels, multiple station-related outlines, and non-adjacent land blocks.
- Consolidate overlapping "building", "underground space", and "underground outline" concepts into one explicit space model so 2D geometry and 3D extrusion stay consistent.
- Add project intake import/export, custom project naming, station search, station memory, and station-type autofill based on existing station data or line count.
- Fix and verify report export end to end, including browser download behavior and export history.
- Improve report content and structure: align with the legacy report format, strengthen hierarchy, add ridership and old-city-protection dimensions where data exists, and add safety/rail-protection notice content at the end.
- Reserve integration surfaces for generated-image APIs, administrator-maintained station outlines, user accounts, and server migration without making those dependencies block the core T0 fixes.

## Capabilities

### New Capabilities

- `schematic-authoring-export`: Covers schematic geometry authoring, multi-object drawing, layer management, 3D view adjustment, and PNG export/download behavior.
- `project-intake-station-context`: Covers project intake import/export, project naming, station search, station memory, station-type autofill, and administrator-maintained station outline records.
- `report-export-content-quality`: Covers report export reliability, exported file access, report format alignment, content hierarchy, and additional report dimensions/notices.
- `platform-readiness`: Covers user accounts, server migration readiness, and generated-image API placeholders required by the feedback but not necessarily implemented in the first core slice.

### Modified Capabilities

- None. This repository does not yet contain baseline OpenSpec specs, so the feedback is captured as new capability specs.

## Impact

- Frontend schematic page: `outputs/interconnect_agent_system/frontend/schematic/index.html` and related scripts such as `space_model.js` and `export_current_view.cjs`.
- Backend schematic APIs: `/api/schematic/user-geometry` and `/api/schematic/export-png` in `outputs/interconnect_agent_system/backend/server.py`.
- Frontend workbench/project intake: `outputs/interconnect_agent_system/frontend/index.html` and `outputs/interconnect_agent_system/frontend/assets/app.js`.
- Backend project, station, and export APIs: `/api/projects`, `/api/evaluate`, `/api/export`, `/api/exports`, and station-context helpers in `outputs/interconnect_agent_system/backend/server.py`.
- Report generation code in `outputs/interconnect_agent_system/backend/server.py` and `outputs/interconnect_agent_system/backend/research_agent.py`.
- Data files under `outputs/interconnect_agent_system/data/`, especially station, ridership, operations, amenities, project, and schematic geometry data.
- Verification scripts under `outputs/interconnect_agent_system/tools/` and top-level schematic/system verification scripts.
