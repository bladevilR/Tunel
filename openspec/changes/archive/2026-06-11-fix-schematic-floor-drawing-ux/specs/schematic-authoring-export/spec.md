## MODIFIED Requirements

### Requirement: Live drawing guidance
The schematic page SHALL show a temporary guide line or preview shape from the last confirmed point to the current mouse position while a drawing operation is active, including after the mouse button has been released.

#### Scenario: Preview second point before confirmation
- **WHEN** a user has clicked the first point of a line or polygon and then moves the mouse without holding any button
- **THEN** the page displays a temporary guide segment from the confirmed point to the current cursor position, and the segment becomes committed only after the user clicks the next point

#### Scenario: Preview polygon closure while adding points
- **WHEN** a user has placed at least two points for a polygon and moves the cursor before confirming the next point
- **THEN** the page displays a temporary preview shape using the cursor position while keeping already confirmed edges visually stable

#### Scenario: Clear preview after completion or cancel
- **WHEN** a user completes, cancels, or switches away from the active drawing tool
- **THEN** the temporary preview overlay is removed and no stale guide line remains on either map

### Requirement: Unified spatial item model
Buildings, ground spaces, and underground spaces SHALL use one normalized spatial item model with `spaceType`, `groundFloors`, `undergroundFloors`, geometry path, and 3D rendering metadata.

#### Scenario: Convert a building to underground space
- **WHEN** a user changes a spatial item from ground to underground
- **THEN** the 2D style, labels, floor summary, and 3D extrusion update from the same item data without requiring a separate underground-outline object

#### Scenario: Enforce floor limits
- **WHEN** a user enters an above-ground floor count greater than 30
- **THEN** the system clamps or rejects the value so the saved spatial item never exceeds 30 above-ground floors

#### Scenario: Render floor count visibly
- **WHEN** a spatial item has configured above-ground or underground floor counts and custom 3D blocks are visible
- **THEN** the 3D overlay and exported PNG show clear layer bands or grouped floor markers plus a text label that matches the saved `groundFloors` and `undergroundFloors` values

#### Scenario: Preserve floor values through save and export
- **WHEN** a user edits floor counts, saves the schematic, reloads it, and exports PNG
- **THEN** the reloaded inspector, saved geometry JSON, 3D overlay, and PNG export metadata all report the same floor values
