const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const app = fs.readFileSync(path.join(root, "frontend", "assets", "app.js"), "utf8");
const html = fs.readFileSync(path.join(root, "frontend", "index.html"), "utf8");
const server = fs.readFileSync(path.join(root, "backend", "server.py"), "utf8");

assert.match(server, /def search_stations\(/, "backend should expose a station search helper");
assert.match(server, /def station_context_payload\(/, "backend should expose a station context helper");
assert.match(server, /def save_station_memory_record\(/, "backend should expose station memory save helper");
assert.match(server, /def apply_station_memory_payload\(/, "backend should expose station memory apply helper");
assert.match(server, /"\/api\/stations\/search"/, "backend should route station search API");
assert.match(server, /"\/api\/stations\/context"/, "backend should route station context API");
assert.match(server, /"\/api\/station-memory"/, "backend should route station memory API");
assert.match(server, /"\/api\/station-memory\/apply"/, "backend should route station memory apply API");

assert.match(html, /id="exportProjectIntakeBtn"/, "toolbar should include project intake export button");
assert.match(html, /id="importProjectIntakeBtn"/, "toolbar should include project intake import button");
assert.match(html, /id="importProjectIntakeFile"/, "toolbar should include hidden project intake file input");
assert.match(html, /id="stationSearchResults"/, "station form should include explicit search result panel");
assert.match(html, /id="saveStationMemoryBtn"/, "station context panel should include save memory button");
assert.match(html, /id="applyStationMemoryBtn"/, "station context panel should include apply memory button");
assert.match(html, /id="stationMemoryStatus"/, "station context panel should expose memory status");

assert.match(app, /function projectIntakePayload\(/, "frontend should build versioned project intake JSON");
assert.match(app, /function exportProjectIntake\(/, "frontend should export project intake JSON");
assert.match(app, /function importProjectIntakeFile\(/, "frontend should import project intake JSON");
assert.match(app, /function validateProjectIntakePayload\(/, "frontend should validate imported intake JSON");
assert.match(app, /function searchStationSuggestions\(/, "frontend should search station suggestions");
assert.match(app, /function applyStationContext\(/, "frontend should apply selected station context");
assert.match(app, /function saveStationMemory\(/, "frontend should save station memory");
assert.match(app, /function applyStationMemory\(/, "frontend should apply station memory");
assert.match(app, /function findStationMemory\(/, "frontend should use bootstrap station memory fallback");
assert.match(app, /\/api\/stations\/search\?q=/, "frontend should call station search API");
assert.match(app, /\/api\/stations\/context\?name=/, "frontend should call station context API");
assert.match(app, /\/api\/station-memory/, "frontend should call station memory API");
assert.match(app, /structuredClone\(state\.currentProject \|\| \{\}\)/, "collectProject should preserve project metadata such as stationMemorySnapshot");

const ownershipBlock = app.match(/function bindStationAutofillOwnership\(\)[\s\S]*?\r?\n}\r?\n/);
assert.ok(ownershipBlock, "station autofill ownership binding should exist");
assert.match(
  ownershipBlock[0],
  /\[name="station\.stationType"\]/,
  "station type should preserve manual overrides like other autofilled station fields"
);

console.log(JSON.stringify({ ok: true }, null, 2));
