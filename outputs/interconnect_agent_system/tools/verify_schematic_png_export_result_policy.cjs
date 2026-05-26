const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const scriptPath = path.join(root, "frontend", "schematic", "export_current_view.cjs");
const htmlPath = path.join(root, "frontend", "schematic", "index.html");
const source = fs.readFileSync(scriptPath, "utf8");
const html = fs.readFileSync(htmlPath, "utf8");

assert.match(source, /function classifyPageErrors/, "export script should classify fatal and nonfatal page errors");
assert.match(source, /pageWarnings/, "export result should preserve nonfatal page errors as warnings");
assert.doesNotMatch(source, /ok:\s*pageErrors\.length\s*===\s*0/, "nonfatal page warnings should not fail a completed screenshot");
assert.match(html, /body\[data-export="true"\]\s+\.drawbar/, "export mode should hide the drawing toolbar from the PNG");

console.log(JSON.stringify({ ok: true }, null, 2));
