## Context

The current project context can search station data and apply administrator station outlines, but the workflow is still mostly project-local. Repeated studies of the same station need remembered station aliases, corrected station type, common exits/outlines, and reusable notes that can be applied deliberately to new projects.

## Goals / Non-Goals

**Goals:**

- Define a station memory record that is separate from user project records.
- Support deliberate save/apply flows with source metadata and snapshot semantics.
- Improve station search/autofill while preserving manual project overrides.

**Non-Goals:**

- Build a full multi-user permission system; that belongs to platform integration.
- Replace authoritative external data sources. Station memory can store operator-maintained corrections, but source provenance must remain visible.

## Decisions

- Use a versioned local JSON store first, with a schema that can later migrate to a database.
- Store station-memory fields as typed groups: identity/aliases, context values, schematic assets, notes, and provenance.
- Applying memory to a project creates a copied snapshot with `sourceMemoryId`, `sourceVersion`, and `appliedAt`; later station-memory edits do not retroactively change the saved project.
- Search ranking should combine base station data, ridership, operations, amenities, and station memory instead of replacing existing indexes.

## Risks / Trade-offs

- Local JSON can become hard to merge if many operators edit it. Mitigation: version records and keep writes narrow until a database migration exists.
- Memory records may conflict with official source data. Mitigation: display source labels and let user choose whether to apply memory or keep official/autofilled values.
- Applying too many fields automatically can surprise users. Mitigation: require explicit apply actions for schematic outlines and non-basic context notes.
