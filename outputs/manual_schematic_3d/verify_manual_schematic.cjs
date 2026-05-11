const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const annotationsPath = path.join(root, "annotations.json");
const htmlPath = path.join(root, "index.html");
const pngPath = path.join(root, "manual_schematic_3d.png");

function fail(message) {
  throw new Error(message);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function signedArea(points) {
  let area = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    area += a[0] * b[1] - b[0] * a[1];
  }
  return area / 2;
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

function assert(condition, message) {
  if (!condition) fail(message);
}

assert(fs.existsSync(annotationsPath), "annotations.json is missing");
assert(fs.existsSync(htmlPath), "index.html is missing");
assert(fs.existsSync(pngPath), "manual_schematic_3d.png is missing; run render_manual_schematic.cjs first");

const annotations = readJson(annotationsPath);
const parcel = annotations.layers.parcel.points;
const river = annotations.layers.river.points;
const building = annotations.layers.proposedBuilding.footprint;
const channel = annotations.layers.channel.centerline;
const exit = annotations.layers.station.exitPoint;

assert(annotations.canvas.width === 1536, "canvas width should match the review reference width");
assert(annotations.canvas.height === 1024, "canvas height should match the review reference height");
assert(parcel.length >= 6, "parcel redline should have enough vertices to follow the river edge");
assert(Math.abs(signedArea(parcel)) > 100000, "parcel redline area is too small");

const southParcelPoints = parcel.filter((point) => point[1] > 720);
assert(southParcelPoints.length >= 2, "parcel redline must include a southern edge near the river");
assert(river.some((riverPoint) => southParcelPoints.some((parcelPoint) => distance(riverPoint, parcelPoint) < 130)),
  "parcel redline should visibly track the river edge");

assert(building.every((point) => pointInPolygon(point, parcel)),
  "all proposed building footprint points must sit inside the parcel redline");

assert(distance(channel[0], exit) < 70,
  "channel centerline must begin at the station exit");
assert(channel.some((point) => building.some((corner) => distance(point, corner) < 160)),
  "channel centerline must connect toward the proposed building");

const requiredLabels = ["群力地铁站", "1号口", "邻里中心", "地块红线"];
const labels = annotations.labels.map((item) => item.text);
for (const label of requiredLabels) {
  assert(labels.some((text) => text.includes(label)), `missing label: ${label}`);
}

const pngBytes = fs.statSync(pngPath).size;
assert(pngBytes > 100000, "rendered PNG is unexpectedly small");

console.log(JSON.stringify({
  ok: true,
  checked: {
    parcelVertices: parcel.length,
    labels: labels.length,
    pngBytes
  }
}, null, 2));
