const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = __dirname;
const geometryPath = path.join(root, "geometry.js");
const htmlPath = path.join(root, "index.html");
const serverPath = path.join(root, "serve_amap_sync.py");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function pointInPolygon(point, polygon) {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersects = ((yi > y) !== (yj > y))
      && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
    if (intersects) inside = !inside;
  }
  return inside;
}

function distance(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

assert(fs.existsSync(geometryPath), "geometry.js is missing");
assert(fs.existsSync(htmlPath), "index.html is missing");
assert(fs.existsSync(serverPath), "serve_amap_sync.py is missing");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(geometryPath, "utf8"), context);
const geometry = context.window.AMAP_SYNC_GEOMETRY;

assert(geometry, "AMAP_SYNC_GEOMETRY was not exported");
assert(Array.isArray(geometry.parcel.path), "parcel path must be an array");
assert(Array.isArray(geometry.channel.path), "channel footprint must be an array");
assert(Array.isArray(geometry.station.path), "station path must be an array");
assert(Array.isArray(geometry.station.body), "station body must be an array");
assert(JSON.stringify(geometry.station.path) === JSON.stringify(geometry.station.body),
  "station path and Canvas body must be the same coordinates");
assert(geometry.proposedBuilding.path.every((point) => pointInPolygon(point, geometry.parcel.path)),
  "proposed building must stay inside the redline");
if (geometry.channel.centerline.length > 0 && geometry.station.exitPoint) {
  assert(distance(geometry.channel.centerline[0], geometry.station.exitPoint) < 0.00008,
    "channel centerline must begin at station exit");
}

const html = fs.readFileSync(htmlPath, "utf8");
assert(html.includes("map2d") && html.includes("map3d"), "HTML must include both 2D and 3D maps");
assert(html.includes("window.__AMAP_SYNC__"), "HTML must expose runtime sync summary");
assert(html.includes("geometry.js"), "HTML must load shared geometry.js");
assert(html.includes("AMap.MouseTool"), "HTML must load AMap.MouseTool for manual drawing");
assert(html.includes('data-draw-tool="parcel"'), "HTML must include parcel drawing tool");
assert(html.includes('data-draw-tool="channel"'), "HTML must include channel drawing tool");
assert(html.includes('data-draw-tool="exit"'), "HTML must include exit marker drawing tool");
assert(html.includes("saveUserGeometry"), "HTML must persist manually drawn geometry");
assert(html.includes("exportPng"), "HTML must expose PNG export action");
assert(fs.existsSync(path.join(root, "export_current_view.cjs")), "PNG export script is missing");
assert(fs.existsSync(path.join(root, "user_geometry.json")) || fs.existsSync(path.join(root, "serve_amap_sync.py")),
  "server must be able to persist drawn geometry");

console.log(JSON.stringify({
  ok: true,
  checked: {
    geometryVersion: geometry.meta.version,
    parcelVertices: geometry.parcel.path.length,
    channelVertices: geometry.channel.path.length,
    labels: geometry.labels.length,
    hasTwoMaps: true
  }
}, null, 2));
