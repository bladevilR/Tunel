## Purpose
Define schematic geometry authoring, multi-object editing, unified spatial items, 3D view control, and downloadable PNG export behavior.

## Requirements

### Requirement: Multi-object schematic geometry
The system SHALL support multiple parcels, station outlines, channels, exits, and spatial items in one schematic project using stable object IDs.

#### Scenario: Save a project with non-adjacent parcels and two channels
- **WHEN** a user draws two non-adjacent parcel/redline polygons and two channel centerlines in the schematic page
- **THEN** the saved geometry contains separate ID-addressable records for each parcel and channel without overwriting earlier records

#### Scenario: Load legacy singular geometry
- **WHEN** the system loads a geometry file containing legacy singular fields such as `parcel`, `station`, `channel`, or `underground`
- **THEN** the system exposes equivalent v2 collections while preserving enough legacy-compatible data for existing export code until migration is complete

### Requirement: Layer authoring controls
The schematic page SHALL allow users to select and delete specific drawn parcels, station outlines, channels, exits, and spatial items.

#### Scenario: Delete one item from a layer with multiple items
- **WHEN** a user selects one item from a layer that contains multiple drawn items and confirms deletion
- **THEN** only the selected item is removed and all other items in that layer remain unchanged

#### Scenario: Collapse drawing tools
- **WHEN** a user activates the drawing-panel hide/collapse control
- **THEN** the drawing controls are hidden or minimized while the 2D and 3D map canvases remain usable

### Requirement: Live drawing guidance
The schematic page SHALL show a temporary guide line or preview shape from the last confirmed point to the current mouse position while a drawing operation is active.

#### Scenario: Preview second point before confirmation
- **WHEN** a user has placed the first point of a line or polygon and moves the mouse before clicking the second point
- **THEN** the page displays a temporary guide segment that becomes a solid committed segment only after the user confirms the point

### Requirement: Unified spatial item model
Buildings, ground spaces, and underground spaces SHALL use one normalized spatial item model with `spaceType`, `groundFloors`, `undergroundFloors`, geometry path, and 3D rendering metadata.

#### Scenario: Convert a building to underground space
- **WHEN** a user changes a spatial item from ground to underground
- **THEN** the 2D style, labels, floor summary, and 3D extrusion update from the same item data without requiring a separate underground-outline object

#### Scenario: Enforce floor limits
- **WHEN** a user enters an above-ground floor count greater than 30
- **THEN** the system clamps or rejects the value so the saved spatial item never exceeds 30 above-ground floors

### Requirement: Adjustable 3D view
The schematic page SHALL allow users to adjust the 3D map pitch and rotation used for inspection and export.

#### Scenario: Export uses adjusted view
- **WHEN** a user changes the 3D pitch or rotation and then exports a PNG
- **THEN** the exported PNG reflects the selected 3D view orientation rather than resetting to the default angle

### Requirement: Downloadable PNG export
The schematic PNG export SHALL create a served downloadable artifact and return user-facing metadata including filename, relative path, download URL, content type, and size.

#### Scenario: PNG export completes
- **WHEN** a user clicks "Export PNG" and export succeeds
- **THEN** the page shows a browser-openable download link and does not show only an absolute server filesystem path

#### Scenario: PNG export fails
- **WHEN** the export runtime cannot create the PNG
- **THEN** the page shows a concise actionable error and no stale success link is displayed
