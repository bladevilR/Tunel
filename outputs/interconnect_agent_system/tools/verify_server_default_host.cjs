const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const serverPath = path.join(__dirname, "..", "backend", "server.py");
const source = fs.readFileSync(serverPath, "utf8");

assert.match(source, /host\s*=\s*"0\.0\.0\.0"/, "backend/server.py should default to a broadcast/LAN host");

console.log(JSON.stringify({ ok: true }, null, 2));
