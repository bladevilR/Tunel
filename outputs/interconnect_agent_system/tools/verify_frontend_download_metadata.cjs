const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const appSource = fs.readFileSync(path.join(root, "frontend", "assets", "app.js"), "utf8");
const schematicSource = fs.readFileSync(path.join(root, "frontend", "schematic", "index.html"), "utf8");

const exportReportBlock = appSource.slice(
  appSource.indexOf("async function exportReport"),
  appSource.indexOf("function renderExportHistory")
);
const exportHistoryBlock = appSource.slice(
  appSource.indexOf("function renderExportHistory"),
  appSource.indexOf("function showView")
);
const schematicExportBlock = schematicSource.slice(
  schematicSource.indexOf('document.getElementById("exportPngButton")'),
  schematicSource.indexOf("function initialize", schematicSource.indexOf('document.getElementById("exportPngButton")'))
);

assert.match(exportReportBlock, /item\.downloadUrl/, "report export links should use backend downloadUrl metadata");
assert.match(exportReportBlock, /first\.downloadUrl/, "auto-download should use backend downloadUrl metadata");
assert.match(exportHistoryBlock, /item\.downloadUrl/, "export history links should use backend downloadUrl metadata");
assert.match(schematicExportBlock, /result\.export\.downloadUrl|result\.downloadUrl/, "schematic PNG success should use backend downloadUrl metadata");
assert.doesNotMatch(schematicExportBlock, /outputPath\.split/, "schematic PNG UI should not derive links from absolute outputPath");
assert.match(schematicExportBlock, /resultNode\.textContent\s*=\s*`导出失败：/, "schematic PNG failure should replace stale success links with text");

console.log(JSON.stringify({ ok: true }, null, 2));
