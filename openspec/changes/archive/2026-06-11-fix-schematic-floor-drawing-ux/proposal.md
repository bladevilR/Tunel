## Why

The May feedback says drawing should behave like a red-line rubber band after the first click, and the user later confirmed that the floor/layer visualization is still wrong. The current schematic page has a preview implementation, but it only updates during pointer-drag movement and does not satisfy the click-then-follow-mouse behavior; floor counts also affect prism height without making layer boundaries and underground/ground status clear enough for review.

## What Changes

- Make line and polygon drawing show a live preview segment from the last confirmed point to the current mouse position after the first click, without requiring the mouse button to stay pressed.
- Keep committed points visually distinct from preview geometry until the next click confirms the point.
- Make above-ground and underground floor counts produce clear, inspectable 3D layer bands/labels in the custom schematic overlay.
- Ensure floor inputs, saved geometry, labels, and exported PNGs agree on the same floor values and never exceed the existing 30-floor above-ground cap.
- Add regression coverage for the rubber-band preview and floor/layer export behavior.

## Capabilities

### New Capabilities

### Modified Capabilities

- `schematic-authoring-export`: Tighten drawing-preview behavior and floor/layer visualization requirements for schematic authoring and PNG export.

## Impact

- Frontend schematic drawing event handling in `outputs/interconnect_agent_system/frontend/schematic/index.html`.
- Geometry normalization in `outputs/interconnect_agent_system/frontend/schematic/space_model.js`.
- Schematic verification scripts under `outputs/interconnect_agent_system/tools/`.
- PNG export expectations for schematic outputs.
