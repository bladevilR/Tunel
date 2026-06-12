const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const htmlPath = path.join(__dirname, "..", "frontend", "schematic", "index.html");
const html = fs.readFileSync(htmlPath, "utf8");

for (const id of [
  "toggleDrawbarButton",
  "selectModeButton",
  "activeModeLabel",
  "selectionSummary",
  "deleteSelectedObjectButton",
  "viewPitchInput",
  "viewRotationInput"
]) {
  assert.match(html, new RegExp(`id="${id}"`), `schematic UI should expose ${id}`);
}

for (const mode of ["select", "parcel", "station", "building", "exit", "channel"]) {
  assert.match(html, new RegExp(`data-sketch-mode="${mode}"`), `tool palette should expose ${mode} sketch mode`);
}

for (const group of ["tool-palette", "sketch-actions", "selection-inspector", "output-actions"]) {
  assert.match(html, new RegExp(`class="[^"]*${group}`), `drawbar should group controls in ${group}`);
}

assert.match(html, /const sketchModes = Object\.freeze/, "schematic should define explicit sketch modes");
assert.match(html, /let sketchMode = "select"/, "schematic should default to select mode");
assert.match(html, /document\.body\.dataset\.activeSketchMode/, "body should store active mode without colliding with tool button selectors");
assert.match(html, /querySelectorAll\("button\[data-sketch-mode\]"\)/, "sketch mode updates should target only tool buttons");
assert.match(html, /function setSketchMode\(/, "schematic should switch mode through a single state function");
assert.match(html, /function updateSelectionInspector\(/, "schematic should keep the selected-object inspector current");
assert.match(html, /function cancelActiveDrawing\(/, "schematic should provide a reusable drawing cancel path");
assert.match(html, /function undoLastDrawingPoint\(/, "schematic should provide a reusable drawing undo path");
assert.match(html, /function bindSketchKeyboardShortcuts\(/, "schematic should bind keyboard shortcuts for drawing");
for (const shortcut of ["Escape", "Enter", "z", "Delete", "Backspace"]) {
  assert.match(html, new RegExp(`event\\.key === "${shortcut}"`), `schematic should support ${shortcut} keyboard workflow`);
}

assert.match(html, /let drawingPreviewPoint/, "drawing should track the current preview cursor point");
assert.match(html, /let drawingPreviewOverlay/, "drawing should keep tentative preview geometry separate from committed geometry");
assert.match(html, /function updateDrawingPreviewOverlay\(/, "drawing should render live preview overlays");
assert.match(html, /updateDrawingPreviewOverlay\(state/, "pointer movement should refresh the live preview overlay");
assert.match(html, /"pointermove", "mousemove", "touchmove"/, "drawing preview should listen to mouse movement after click");
assert.match(html, /if \(!activeDrawTool\) \{[\s\S]*?return;[\s\S]*?const point = drawingPointerPoint\(event\);/, "pointer movement should not require pointerdown before computing preview point");
assert.match(html, /drawingPointerStart && Math\.hypot/, "drag suppression should still be limited to actual pointer-drag gestures");

assert.match(html, /function selectDrawObject\(/, "schematic should support selecting drawn objects");
assert.match(html, /function deleteSelectedObject\(/, "schematic should support deleting the selected object");
for (const collection of ["parcels", "stationOutlines", "exits", "channels", "buildings", "spatialItems"]) {
  assert.match(html, new RegExp(`geometry\\.${collection}`), `delete/select should cover geometry.${collection}`);
}
assert.match(html, /geometry\.parcels = \[\.\.\.geometry\.parcels, parcel\]/, "drawing parcel should append to the v2 parcel collection");
assert.match(html, /geometry\.stationOutlines = \[\.\.\.geometry\.stationOutlines, station\]/, "drawing station should append to the v2 station collection");
assert.match(html, /selectedDrawObject = \{ type: "parcel", id: parcel\.id \}/, "new parcel should become selected");
assert.match(html, /selectedDrawObject = \{ type: "station", id: station\.id \}/, "new station should become selected");

assert.match(html, /function setDrawbarCollapsed\(/, "draw toolbar should have a collapse controller");
assert.match(html, /drawbar\.classList\.toggle\("is-collapsed"/, "draw toolbar collapse should be reflected in CSS state");
assert.match(html, /@media \(max-width: 860px\)[\s\S]*overflow: auto;/, "narrow schematic view should remain scrollable");
assert.match(html, /@media \(max-width: 860px\)[\s\S]*min-height: 680px;/, "narrow schematic view should keep enough drawable map area");
assert.match(html, /\.drawbar[\s\S]*max-height: min\(52vh, 420px\);/, "narrow draw toolbar should not consume the whole viewport");

assert.match(html, /function captureViewState\(/, "schematic should capture current 3D map view state");
assert.match(html, /function applyViewStateToMap\(/, "schematic should apply persisted 3D view state");
assert.match(html, /function syncViewStateControls\(/, "schematic should keep view controls in sync");
assert.match(html, /geometry\.viewState\.pitch/, "3D pitch should be persisted in geometry.viewState");
assert.match(html, /geometry\.viewState\.rotation/, "3D rotation should be persisted in geometry.viewState");
assert.match(html, /saveUserGeometry\(state\)/, "PNG export should save current map view state before capture");

console.log(JSON.stringify({ ok: true }, null, 2));
