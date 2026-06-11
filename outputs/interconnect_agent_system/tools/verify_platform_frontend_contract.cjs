const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const app = fs.readFileSync(path.join(root, "frontend", "assets", "app.js"), "utf8");
const server = fs.readFileSync(path.join(root, "backend", "server.py"), "utf8");
const envExample = fs.readFileSync(path.join(root, ".env.example"), "utf8");

assert.match(server, /def server_config\(/, "backend should centralize deployment configuration");
assert.match(server, /def generated_image_response\(/, "backend should expose generated-image provider response");
assert.match(server, /def validate_server_configuration\(/, "backend should validate server configuration");
assert.match(server, /def migrate_project_owner\(/, "backend should expose ownership migration path");
assert.match(server, /current_owner_metadata\("generated_image"\)/, "generated images should include owner metadata");
assert.match(server, /current_owner_metadata\("station_memory"\)/, "station memory should include owner metadata");
assert.match(server, /current_owner_metadata\("project"\)/, "projects should include owner metadata");
assert.match(server, /"\/api\/ownership\/migrate"/, "backend should route ownership migration API");

assert.match(app, /state\.bootstrap\?\.platformCapabilities/, "frontend should read platform capabilities");
assert.match(app, /generatedImage\.provider/, "frontend should display generated-image provider state");
assert.match(app, /deployment\.validation/, "frontend should display deployment validation state");
assert.match(app, /configured: "已配置"/, "frontend capability labels should include configured mode");

for (const key of [
  "INTERCONNECT_HOST",
  "INTERCONNECT_PORT",
  "INTERCONNECT_ACCOUNT_MODE",
  "GENERATED_IMAGE_PROVIDER",
  "INTERCONNECT_EXPORT_PDF",
]) {
  assert.match(envExample, new RegExp(key), `.env.example should document ${key}`);
}

console.log(JSON.stringify({ ok: true }, null, 2));
