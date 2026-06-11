const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const modelPath = path.join(__dirname, "..", "frontend", "schematic", "space_model.js");
const htmlPath = path.join(__dirname, "..", "frontend", "schematic", "index.html");
const spaceModel = require(modelPath);
const repoRoot = path.join(__dirname, "..", "..", "..");
const fixtureRootCandidates = [
  path.join(repoRoot, "openspec", "changes", "address-agent-experience-feedback", "fixtures"),
  path.join(repoRoot, "openspec", "changes", "archive", "2026-05-25-address-agent-experience-feedback", "fixtures")
];
const fixtureRoot = fixtureRootCandidates.find((candidate) => fs.existsSync(candidate));
assert.ok(fixtureRoot, `fixture root not found in: ${fixtureRootCandidates.join(", ")}`);
const html = fs.readFileSync(htmlPath, "utf8");
const saveBlock = html.slice(
  html.indexOf("async function saveUserGeometry"),
  html.indexOf("async function exportPng")
);

assert.equal(spaceModel.normalizeSpaceType("underground"), "underground");
assert.equal(spaceModel.normalizeSpaceType("ground"), "ground");
assert.equal(spaceModel.normalizeSpaceType("bad-value"), "ground");

const ground = spaceModel.volumeProjection({
  spaceType: "ground",
  angleDegrees: -58,
  height: 40
});
const underground = spaceModel.volumeProjection({
  spaceType: "underground",
  angleDegrees: -58,
  height: 40
});

assert.equal(ground.kind, "ground");
assert.equal(ground.dashed, false);
assert.equal(underground.kind, "underground");
assert.equal(underground.dashed, true);
assert.ok(ground.offsetY < 0, "ground volumes should project upward on screen");
assert.ok(underground.offsetY > 0, "underground volumes should project downward on screen");
assert.equal(Math.sign(ground.offsetX), Math.sign(underground.offsetX), "space depth should keep the same diagonal x direction");

const normalized = spaceModel.normalizeSpatialItem({
  name: "建筑 1",
  spaceType: "underground",
  groundFloors: "6",
  undergroundFloors: "2"
});
assert.deepEqual(
  {
    spaceType: normalized.spaceType,
    groundFloors: normalized.groundFloors,
    undergroundFloors: normalized.undergroundFloors
  },
  {
    spaceType: "underground",
    groundFloors: 6,
    undergroundFloors: 2
  }
);
assert.equal(spaceModel.spaceTypeLabel(normalized.spaceType), "地下");
assert.equal(spaceModel.floorSummary(normalized), "地上6层 / 地下2层");
const undergroundDisplay = spaceModel.floorDisplay(normalized);
assert.equal(undergroundDisplay.activeFloors, 2, "underground display should use underground floor count");
assert.equal(undergroundDisplay.bandCount, 2, "two underground floors should render two floor bands");
assert.equal(undergroundDisplay.label, "地下2层", "floor display label should name active underground floors");

const overLimit = spaceModel.normalizeSpatialItem({
  spaceType: "ground",
  groundFloors: 99,
  undergroundFloors: 2
});
assert.equal(overLimit.groundFloors, 30, "above-ground floors should be capped at 30");
const overLimitDisplay = spaceModel.floorDisplay(overLimit);
assert.equal(overLimitDisplay.activeFloors, 30, "floor display should preserve exact capped floor count");
assert.equal(overLimitDisplay.bandCount, 10, "tall floor counts should render grouped floor bands");
assert.equal(overLimitDisplay.groupSize, 3, "30 floors should group into ten three-floor bands");
assert.equal(overLimitDisplay.grouped, true, "grouped flag should be true for tall floor counts");

const zeroGround = spaceModel.floorDisplay({
  spaceType: "ground",
  groundFloors: 0,
  undergroundFloors: 0
});
assert.equal(zeroGround.activeFloors, 0, "zero-floor items should keep exact active floor count");
assert.equal(zeroGround.visualFloors, 1, "zero-floor items should still keep a minimal visual prism height");

const legacyGeometry = JSON.parse(fs.readFileSync(path.join(fixtureRoot, "legacy_geometry.json"), "utf8"));
const normalizedLegacy = spaceModel.normalizeGeometryV2(legacyGeometry);
assert.equal(normalizedLegacy.schemaVersion, "schematic-geometry.v2");
assert.equal(normalizedLegacy.parcels.length, 1, "legacy parcel should migrate into parcels collection");
assert.equal(normalizedLegacy.stationOutlines.length, 1, "legacy station body should migrate into stationOutlines collection");
assert.equal(normalizedLegacy.exits.length, 1, "legacy station exit should migrate into exits collection");
assert.equal(normalizedLegacy.channels.length, 1, "legacy channel should migrate into channels collection");
assert.equal(normalizedLegacy.spatialItems.length, 1, "legacy underground outline should migrate into spatialItems collection");
assert.equal(normalizedLegacy.parcel.id, normalizedLegacy.parcels[0].id, "legacy parcel alias should point at first parcel");
assert.equal(normalizedLegacy.channel.id, normalizedLegacy.channels[0].id, "legacy channel alias should point at selected channel");

const v2Geometry = JSON.parse(fs.readFileSync(path.join(fixtureRoot, "geometry_v2_two_parcels_channels.json"), "utf8"));
const normalizedV2 = spaceModel.normalizeGeometryV2(v2Geometry);
assert.equal(normalizedV2.parcels.length, 2, "v2 geometry should keep two parcels");
assert.equal(normalizedV2.channels.length, 2, "v2 geometry should keep two channels");
assert.equal(normalizedV2.spatialItems.length, 2, "v2 geometry should keep two spatial items");
assert.equal(normalizedV2.viewState.pitch, 42, "v2 view state should be preserved");

assert.match(html, /id="groundFloorsInput"[^>]*max="30"/, "ground floor input should cap at 30 floors");
assert.match(html, /spaceModel\.normalizeGeometryV2\(geometry\)/, "schematic page should normalize geometry through the shared model");
assert.match(html, /spaceModel\.floorDisplay\(item\)/, "schematic rendering should use shared floor display calculations");
assert.match(html, /floorBands: options\.floorBands \?\? display\.bandCount/, "3D prism rendering should use actual floor band counts");
assert.match(saveBlock, /ensureGeometryV2\(\)/, "saving should normalize geometry before POST");
assert.match(saveBlock, /JSON\.stringify\(geometry\)/, "saving should persist normalized geometry");
assert.doesNotMatch(html, /data-draw-tool="underground"/, "underground outline should not remain a separate drawing tool");

console.log(JSON.stringify({ ok: true }, null, 2));
