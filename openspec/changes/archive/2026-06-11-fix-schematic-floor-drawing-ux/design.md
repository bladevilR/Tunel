## Context

The active schematic implementation uses AMap for the 2D/3D map surfaces and a Canvas overlay for custom 3D prisms. Existing code has `drawingPreviewPoint`, but preview updates are gated by a pointer-start state, so after a normal click the next mouse movement does not keep the guide line attached to the cursor. Floor count handling is also mostly numeric: `groundFloors` and `undergroundFloors` alter prism height, but the visual floor bands are not reliable enough to show "how many layers" at review time.

## Goals / Non-Goals

**Goals:**

- Make active drawing feel deterministic: click first point, move mouse, see a temporary red/blue/purple guide line until the next point is clicked.
- Render floor counts as explicit layer bands or markers in custom 3D prisms, with labels matching saved geometry.
- Keep behavior compatible with existing geometry v2 records and PNG export.

**Non-Goals:**

- Replace AMap or introduce a true BIM/GIS 3D engine.
- Change the scoring/report pipeline.
- Add real building-height data from external map providers.

## Decisions

- Track preview movement from map mousemove/pointermove whenever an active drawing tool has at least one committed point. This decouples rubber-band preview from pointer button state.
- Keep preview geometry on the same AMap overlay layer but use dashed/lighter styling until confirmation. This avoids adding another rendering stack while preserving user distinction between tentative and committed geometry.
- Centralize floor display math in `space_model.js` so labels, Canvas prism height, and verification fixtures use the same normalized values.
- For tall buildings, use capped visual bands plus a numeric label rather than drawing 30 dense lines if the result becomes unreadable. The cap remains data-level 30 floors; the display can group layers while still showing the exact count.

## Risks / Trade-offs

- Preview event handling can interfere with map panning if drawing mode locking is too broad. Mitigation: only lock map gestures while a drawing tool is active and test selection/panning after exiting drawing mode.
- Dense floor lines can clutter PNG exports. Mitigation: group visual bands at high floor counts and require exact text labels.
- Custom prism visibility depends on the "self-built block" toggle. Mitigation: floor verification must enable the custom overlay and assert that exported PNG metadata/rendering reflects it.
