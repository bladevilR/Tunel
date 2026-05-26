## 1. Baseline And Scope Locks

- [x] 1.1 Select the canonical legacy report reference and record the chosen file plus expected top-level section order in the implementation notes.
- [x] 1.2 Capture one sample project fixture that exercises station context, report export, and schematic linkage.
- [x] 1.3 Capture one legacy schematic geometry fixture and one target v2 geometry fixture covering two parcels and two channels.
- [x] 1.4 Run the current report export and PNG export paths once and record the observed failure/success behavior for regression comparison.

## 2. T0 Export Reliability

- [x] 2.1 Update backend export metadata helpers to return `filename`, `relativePath`, `downloadUrl`, `contentType`, and `size` for report and PNG artifacts.
- [x] 2.2 Make `/api/export` return served download URLs for all generated report artifacts and keep export history compatible.
- [x] 2.3 Update the report export frontend to render all returned files and trigger download only from served URLs.
- [x] 2.4 Make `/api/schematic/export-png` return served PNG download metadata instead of only an absolute filesystem path.
- [x] 2.5 Update the schematic PNG export UI message so success shows a local browser-openable link and failure shows an actionable error.
- [x] 2.6 Add verification for report export: generated files exist, are non-empty, appear in `/api/exports`, and have valid download URLs.
- [x] 2.7 Add verification for PNG export metadata and stale-link prevention on failed export.

## 3. T0 Schematic Geometry Model

- [x] 3.1 Define a geometry v2 normalization module for parcels, station outlines, exits, channels, spatial items, labels, view state, and source metadata.
- [x] 3.2 Add legacy-to-v2 adapters for existing `parcel`, `station`, `channel`, `proposedBuilding`, `buildings`, `underground`, and `channels` fields.
- [x] 3.3 Update schematic load/save to persist v2 collections while retaining legacy-compatible aliases during the migration window.
- [x] 3.4 Replace user-facing underground-outline behavior with the unified spatial item model or map existing underground outlines into spatial items.
- [x] 3.5 Enforce above-ground floor limits at 30 in UI inputs, normalization helpers, and saved geometry.
- [x] 3.6 Update 2D and 3D rendering to draw multiple parcels, station outlines, channels, exits, and spatial items from v2 collections.
- [x] 3.7 Add tests for legacy geometry loading, v2 saving, multiple channels, non-adjacent parcels, and floor-limit clamping.

## 4. T0 Project Intake And Station Context

- [x] 4.1 Add a versioned project-intake export endpoint or frontend download path using the saved project record format.
- [x] 4.2 Add project-intake import validation and form population, including clear errors for incompatible JSON.
- [x] 4.3 Ensure custom project names are preserved in save/load, project selector display, report title fallback, and export slug generation.
- [x] 4.4 Add station search/context API coverage over station, ridership, operations, amenities, and station-index data.
- [x] 4.5 Add frontend station search suggestions with source labels and explicit user selection.
- [x] 4.6 Use selected station context to autofill line, TOD/location level, daily inbound, nearby exit/context summaries, and station type.
- [x] 4.7 Preserve manual overrides for autofilled station fields and keep source metadata distinguishable.
- [x] 4.8 Add station-type inference tests for transfer stations, normal stations, and manual overrides.

## 5. T1 Schematic Authoring UX

- [x] 5.1 Add live mouse-follow guide lines or preview shapes for active line and polygon drawing.
- [x] 5.2 Add selection state and delete controls for individual parcels, station outlines, exits, channels, and spatial items.
- [x] 5.3 Add a drawing-tool hide/collapse control that keeps both maps usable.
- [x] 5.4 Add 3D pitch/rotation controls and persist the chosen view state in schematic geometry.
- [x] 5.5 Make PNG export use the persisted or current 3D view state instead of resetting to a default view.
- [x] 5.6 Verify the schematic page visually in desktop and narrower viewports after the tool-panel and 3D-view changes.

## 6. T1 Report Content Quality

- [x] 6.1 Refactor report generation into deterministic section builders that match the selected legacy report section order.
- [x] 6.2 Add report checks for readable hierarchy across facts, basis, station context, scoring, recommendation, risks, data gaps, and implementation suggestions.
- [x] 6.3 Add ridership content with source and judgement impact when station ridership data is available.
- [x] 6.4 Add old-city protection handling that uses authoritative data when present and otherwise emits a manual verification item.
- [x] 6.5 Add safety and rail-protection requirements notice content near the end of the formal report or in an appendix.
- [x] 6.6 Add report regression verification for section order, required notices, data-source wording, and non-empty DOCX/PDF outputs.

## 7. T2 Platform Readiness

- [x] 7.1 Add explicit feature flags or capability status fields for generated-image API, accounts, admin data, and server deployment features.
- [x] 7.2 Add a generated-image API placeholder endpoint or client contract that returns structured "not configured" responses when disabled.
- [x] 7.3 Add a minimal local anonymous identity contract so future account support can attach ownership without blocking local use.
- [x] 7.4 Define shared administrator station-outline storage separately from user project data.
- [x] 7.5 Add apply-to-project behavior for administrator station outlines with source metadata or snapshot semantics.
- [x] 7.6 Update deployment/server migration documentation for host, port, data paths, export paths, runtime dependencies, and secret/API-key settings.

## 8. Final Verification And Handoff

- [x] 8.1 Run backend syntax checks for changed Python files.
- [x] 8.2 Run existing Node verification scripts plus new export, geometry, station, and report verification scripts.
- [x] 8.3 Start the local server and verify core user flows in the browser: project import/export, station search/autofill, report export, schematic save, and PNG export.
- [x] 8.4 Update delivery notes or handoff documentation with completed items, remaining T2 items, and known operational limits.
- [x] 8.5 Review git diff to ensure generated artifacts and unrelated user changes are not accidentally reverted or committed.
