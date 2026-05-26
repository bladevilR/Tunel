const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const htmlPath = path.join(__dirname, "..", "frontend", "schematic", "index.html");
const html = fs.readFileSync(htmlPath, "utf8");

assert.match(html, /id="channelSelect"/, "schematic toolbar should expose a channel selector");
assert.match(html, /geometry\.channels/, "schematic geometry should use a channels collection");
assert.match(html, /geometry\.parcels/, "schematic geometry should use a parcels collection");
assert.match(html, /geometry\.stationOutlines/, "schematic geometry should use a stationOutlines collection");
assert.match(html, /geometry\.spatialItems/, "schematic geometry should use a spatialItems collection");
assert.match(html, /geometry\.parcels\.map/, "schematic rendering should draw every parcel");
assert.match(html, /geometry\.stationOutlines\.map/, "schematic rendering should draw every station outline");
assert.match(html, /geometry\.spatialItems\.map/, "schematic rendering should draw every spatial item");
assert.match(html, /function getSelectedChannel\(/, "schematic should support selecting one channel");
assert.match(html, /function addChannel\(/, "schematic should append new channels instead of overwriting the legacy channel");
assert.doesNotMatch(
  html,
  /geometry\.channel\.centerline\s*=\s*\[start,\s*mid,/,
  "auto channel generation must not overwrite the single legacy channel directly"
);

console.log(JSON.stringify({ ok: true }, null, 2));
