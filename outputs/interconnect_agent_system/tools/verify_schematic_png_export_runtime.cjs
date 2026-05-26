const assert = require("node:assert");
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const scriptPath = path.join(root, "frontend", "schematic", "export_current_view.cjs");

const env = { ...process.env };
delete env.NODE_PATH;

const completed = spawnSync(process.execPath, [scriptPath, "--check-runtime"], {
  cwd: path.dirname(scriptPath),
  env,
  encoding: "utf8"
});

assert.strictEqual(
  completed.status,
  0,
  `runtime check failed\nSTDOUT:\n${completed.stdout}\nSTDERR:\n${completed.stderr}`
);

const result = JSON.parse(completed.stdout);
assert.strictEqual(result.ok, true);
assert.strictEqual(result.automation, "chrome-devtools-protocol");
assert.strictEqual(result.externalAutomationDependency, false);

console.log(JSON.stringify(result, null, 2));
