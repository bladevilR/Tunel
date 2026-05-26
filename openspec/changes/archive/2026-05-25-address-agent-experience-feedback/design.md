## Context

The current MVP already has a local HTTP server, a browser-based workbench, a schematic page, project persistence, station context lookup, and report export endpoints. The feedback document points to two kinds of issues:

- Core pilot blockers: report export, PNG export/download, project import/export, station lookup/autofill, and reliable schematic editing.
- Product-readiness items: administrator station outlines, user accounts, server migration, generated-image API placeholders, and report content refinements.

The implementation must respect the existing local-first delivery package and avoid requiring new external services for the first usable slice.

## Goals / Non-Goals

**Goals:**

- Deliver a T0 slice that fixes export blockers and makes repeated project/station work reliable.
- Preserve existing project and schematic data while migrating to richer multi-object data structures.
- Keep report generation deterministic and testable, with explicit data sources and fallback behavior.
- Define platform-readiness hooks without forcing account/auth or image-generation services into the first implementation pass.

**Non-Goals:**

- Full multi-user permission management in the first slice.
- Final production deployment automation for every target server environment.
- Engineering-grade CAD/BIM drawings, construction drawings, or authoritative rail-protection approvals.
- Generated schematic imagery from an external image API before the local schematic workflow is stable.

## Decisions

### Decision 1: Use a compatibility-first schematic geometry v2 model

Represent parcels, station outlines, channels, buildings/spaces, exits, and labels as arrays with stable IDs. Keep legacy singular keys such as `parcel`, `station`, `channel`, `proposedBuilding`, and `underground` as read-compatible aliases during migration.

Rationale: the feedback explicitly requires multiple parcels, channels, and station-related outlines. A direct rewrite would risk breaking existing saved geometry and export scripts; an adapter lets the UI and backend accept both shapes.

Alternatives considered:

- Replace the JSON shape in one pass. This is simpler but risks data loss and fragile tests.
- Keep adding one-off singular fields. This would not solve non-adjacent parcels or multiple channels.

### Decision 2: Treat underground space as a space type, not a separate drawing primitive

Use a single spatial item model with `spaceType`, `groundFloors`, `undergroundFloors`, and geometry/path fields. Remove the user-facing "underground outline" workflow after migration, or map it into the same spatial-item collection.

Rationale: the document notes that building-to-underground conversion overlaps with underground-outline drawing and that underground outline cannot become 3D. One model keeps 2D and 3D synchronized.

Alternatives considered:

- Keep underground outline as a separate primitive. This preserves current UI labels but continues the duplicate behavior.
- Only allow buildings to become underground. This is clean, but migration must still accept existing `underground` payloads.

### Decision 3: Export APIs return user-facing download metadata

For report and schematic exports, the backend SHALL return `filename`, `relativePath`, `downloadUrl`, `contentType`, and `size` for each generated artifact. The frontend SHALL render links and trigger a browser download only after the file exists and is served by the static export route.

Rationale: the feedback says PNG export appears to exist only on the server. Returning a filesystem path is not enough for a user. This also gives report export a consistent verification target.

Alternatives considered:

- Keep returning absolute paths and instruct users where to look. This does not satisfy the local-download expectation.
- Stream the file directly from POST. This complicates multi-file report exports and export history.

### Decision 4: Project intake import/export uses the saved project record format

Project import/export should serialize a record containing project data, research options, linked schematic metadata, and a schema/version marker. It should not include generated reports by default; reports remain export artifacts.

Rationale: users need to move or archive project intake data independently from generated outputs. Versioned JSON gives a durable interchange format and can be validated before saving.

Alternatives considered:

- Export only form fields. This loses research options and linkage.
- Export a zip with all generated outputs. Useful later, but too heavy for the intake-page requirement.

### Decision 5: Station context becomes a reusable lookup/autofill service

Expose station search and station-context endpoints backed by existing station, ridership, operations, amenities, and station-index data. The frontend uses these endpoints for search suggestions, station-type autofill, daily inbound values, and station metadata.

Rationale: station-type autofill and station memory both depend on the same indexed station facts. Centralizing lookup prevents separate UI-only heuristics from drifting.

Alternatives considered:

- Compute everything in the browser from bootstrapped data. This is faster to prototype but duplicates backend logic and source matching.
- Require manual station entry. This does not address the feedback.

### Decision 6: Report improvements are template and content-source changes, not freeform rewrites

Align report structure with the legacy reference by updating section order, headings, appendices/notices, and deterministic content builders. Add ridership, old-city protection, safety, and rail-protection sections only when data or explicit rule text is available; otherwise show them as required follow-up checks.

Rationale: reports must be trusted as planning material. Template-driven changes are easier to test than allowing unrestricted prose generation.

Alternatives considered:

- Rewrite the report entirely with an LLM. This is not reliable enough for deterministic exports.
- Add static text to every report. This risks making unsupported claims for stations without relevant data.

### Decision 7: Platform-readiness items are staged behind clear interfaces

Define lightweight placeholders for admin station-outline records, account identity, server migration settings, and generated-image API calls. Implement only the data contracts and feature flags needed by T0/T1 work unless a later task explicitly enables the full capability.

Rationale: the feedback names these needs, but they are larger than the immediate export and drawing blockers. Interfaces prevent rework while keeping the first release scoped.

Alternatives considered:

- Implement accounts and server migration first. This delays user-visible fixes.
- Ignore these items. This would leave no path for the next delivery stage.

## Risks / Trade-offs

- Geometry migration could break existing saved sketches -> Mitigate with adapter tests for legacy and v2 payloads, plus a one-time migration script.
- PNG export may still depend on a local browser/runtime environment -> Mitigate with explicit error messages, runtime checks, and a verification script that asserts a served download URL.
- Station matching can be ambiguous for aliases and duplicate names -> Mitigate with ranked suggestions, source labels, and manual override.
- Report format alignment may be subjective without a chosen "old version" reference -> Mitigate by selecting one reference DOCX/PDF before implementation and capturing visible section-order expectations in tests.
- User accounts and server migration can expand scope quickly -> Mitigate by treating them as T2 contracts unless the user promotes them.

## Migration Plan

1. Add geometry normalization helpers that load legacy geometry and emit v2 collections without deleting legacy fields.
2. Update schematic save/export to write v2 while still serving legacy-compatible fields.
3. Add project intake import/export endpoints and frontend controls using versioned JSON.
4. Update report and PNG export response metadata, then verify browser links and export history.
5. Add station search/context endpoints and use them for autofill and station memory.
6. Update report template/content builders and add regression checks against expected section names.
7. Add platform-readiness contracts and documentation for items deferred beyond T0/T1.

Rollback is file-based: keep previous JSON backups for geometry and projects, and preserve existing export endpoints until the new metadata contract passes verification.

## Open Questions

- Which legacy report should be the canonical format reference: `互联互通测试.docx` or one of the files under `03智能体输出成果参考报告/`?
- Should administrator station outlines be global per station, per station+exit, or per station+project scenario?
- Should project import/export include linked schematic geometry inline, by reference, or as a separate optional JSON file?
- For old-city protection, which data source is authoritative in this workspace, and should absent data be shown as "not applicable" or "requires manual check"?
