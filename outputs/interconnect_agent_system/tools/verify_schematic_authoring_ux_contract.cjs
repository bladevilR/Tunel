const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const htmlPath = path.join(__dirname, "..", "frontend", "schematic", "index.html");
const html = fs.readFileSync(htmlPath, "utf8");

for (const id of [
  "toggleDrawbarButton",
  "deleteSelectedObjectButton",
  "viewPitchInput",
  "viewRotationInput"
]) {
  assert.match(html, new RegExp(`id="${id}"`), `schematic UI should expose ${id}`);
}

assert.match(html, /let drawingPreviewPoint/, "drawing should track the current preview cursor point");
assert.match(html, /function updateDrawingPreviewOverlay\(/, "drawing should render live preview overlays");
assert.match(html, /updateDrawingPreviewOverlay\(state/, "pointer movement should refresh the live preview overlay");

assert.match(html, /function selectDrawObject\(/, "schematic should support selecting drawn objects");
assert.match(html, /function deleteSelectedObject\(/, "schematic should support deleting the selected object");
for (const collection of ["parcels", "stationOutlines", "exits", "channels", "buildings", "spatialItems"]) {
  assert.match(html, new RegExp(`geometry\\.${collection}`), `delete/select should cover geometry.${collection}`);
}

assert.match(html, /function setDrawbarCollapsed\(/, "draw toolbar should have a collapse controller");
assert.match(html, /drawbar\.classList\.toggle\("is-collapsed"/, "draw toolbar collapse should be reflected in CSS state");

assert.match(html, /function captureViewState\(/, "schematic should capture current 3D map view state");
assert.match(html, /function applyViewStateToMap\(/, "schematic should apply persisted 3D view state");
assert.match(html, /function syncViewStateControls\(/, "schematic should keep view controls in sync");
assert.match(html, /geometry\.viewState\.pitch/, "3D pitch should be persisted in geometry.viewState");
assert.match(html, /geometry\.viewState\.rotation/, "3D rotation should be persisted in geometry.viewState");
assert.match(html, /saveUserGeometry\(state\)/, "PNG export should save current map view state before capture");

console.log(JSON.stringify({ ok: true }, null, 2));
