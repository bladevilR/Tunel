## 1. Drawing Preview

- [x] 1.1 Audit active drawing event flow and identify where preview updates are gated by pointer-down state.
- [x] 1.2 Update map movement handlers so active line/polygon tools refresh preview after the first confirmed point without requiring mouse drag.
- [x] 1.3 Style tentative preview geometry distinctly from committed geometry and clear it on cancel, finish, undo, and mode switch.

## 2. Floor Visualization

- [x] 2.1 Centralize floor display calculations for ground and underground spatial items in the schematic space model.
- [x] 2.2 Update Canvas prism rendering to show readable layer bands or grouped markers and exact floor labels.
- [x] 2.3 Ensure inspector inputs, saved geometry, labels, custom model toggle, and PNG export use the same normalized floor values.

## 3. Verification

- [x] 3.1 Add a browser verification for click-first-point then mousemove preview behavior.
- [x] 3.2 Add a schematic geometry/rendering verification for 0/1/multi-floor ground and underground cases, including the 30-floor cap.
- [x] 3.3 Run schematic authoring/export verification and record expected screenshots or assertions for the changed behavior.
