const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const serverPath = path.join(__dirname, "..", "backend", "server.py");
const source = fs.readFileSync(serverPath, "utf8");

assert.match(source, /"host": env_first\("INTERCONNECT_HOST", "HOST", default="0\.0\.0\.0"\)/, "server_config should default to a broadcast/LAN host");
assert.match(source, /config = server_config\(\)[\s\S]*host = config\["host"\]/, "main should use centralized server_config host");

console.log(JSON.stringify({ ok: true }, null, 2));
