const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const appPath = path.join(__dirname, "..", "frontend", "assets", "app.js");
const app = fs.readFileSync(appPath, "utf8");

assert.match(app, /function setAutofilledStationField\(/, "station autofill should use ownership-aware field writes");
assert.match(app, /dataset\.stationAutofilled/, "autofilled values should be marked so station changes can refresh them");
assert.match(app, /function bindStationAutofillOwnership\(/, "user edits should be able to take ownership away from autofill");
assert.match(app, /\[name="station\.stationType"\]/, "station type should participate in autofill ownership");
assert.match(app, /inferStationTypeFromLine\(/, "station type should be inferred from line count when context is local");
assert.match(app, /applyStationContext\(/, "station API context should be applied through a shared ownership-aware path");
assert.doesNotMatch(
  app,
  /if \(!\$\('\[name="station\.line"\]'\)\.value\)/,
  "station line must not be protected by the old blank-only condition"
);

console.log(JSON.stringify({ ok: true }, null, 2));
