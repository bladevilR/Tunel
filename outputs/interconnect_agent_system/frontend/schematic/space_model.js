(function initSchematicSpaceModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.SCHEMATIC_SPACE_MODEL = api;
  }
})(typeof window !== "undefined" ? window : globalThis, function createSchematicSpaceModel() {
  const SPACE_TYPES = new Set(["ground", "underground"]);
  const GEOMETRY_SCHEMA_VERSION = "schematic-geometry.v2";
  const MAX_GROUND_FLOORS = 30;

  function normalizeSpaceType(value) {
    return SPACE_TYPES.has(value) ? value : "ground";
  }

  function numberInRange(value, fallback, min, max) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(min, Math.min(max, Math.round(parsed)));
  }

  function normalizeSpatialItem(item = {}, defaults = {}) {
    return {
      ...item,
      spaceType: normalizeSpaceType(item.spaceType || defaults.spaceType),
      groundFloors: numberInRange(item.groundFloors, defaults.groundFloors ?? 4, 0, MAX_GROUND_FLOORS),
      undergroundFloors: numberInRange(item.undergroundFloors, defaults.undergroundFloors ?? 1, 0, 12)
    };
  }

  function clonePoint(point) {
    if (!Array.isArray(point) || point.length < 2) return null;
    const lng = Number(point[0]);
    const lat = Number(point[1]);
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
    return [lng, lat];
  }

  function clonePath(path) {
    if (!Array.isArray(path)) return [];
    return path.map(clonePoint).filter(Boolean);
  }

  function stableId(item, prefix, index) {
    return String(item?.id || `${prefix}-${index + 1}`);
  }

  function normalizePolygonItem(item = {}, defaults = {}, prefix = "item", index = 0) {
    return {
      ...item,
      id: stableId(item, prefix, index),
      name: item.name || defaults.name || `${prefix} ${index + 1}`,
      stroke: item.stroke || defaults.stroke || "#111827",
      fill: item.fill || defaults.fill || "",
      path: clonePath(item.path || item.body || defaults.path)
    };
  }

  function normalizeSpatialCollection(items, defaults = {}, prefix = "space") {
    return (Array.isArray(items) ? items : [])
      .map((item, index) => normalizeSpatialItem({
        ...normalizePolygonItem(item, defaults, prefix, index),
        centerline: clonePath(item.centerline)
      }, defaults));
  }

  function firstWithGeometry(items) {
    return (items || []).find((item) => clonePath(item.path).length || clonePath(item.centerline).length) || null;
  }

  function normalizeGeometryV2(input = {}) {
    const geometry = {
      ...input,
      schemaVersion: GEOMETRY_SCHEMA_VERSION,
      meta: {
        ...(input.meta || {}),
        version: (input.meta || {}).version || GEOMETRY_SCHEMA_VERSION
      },
      viewState: {
        pitch: 38,
        rotation: 0,
        zoom: 16.72,
        ...(input.viewState || {})
      },
      labels: Array.isArray(input.labels) ? [...input.labels] : []
    };

    const parcels = Array.isArray(input.parcels)
      ? input.parcels
      : (input.parcel ? [input.parcel] : []);
    geometry.parcels = parcels.map((item, index) => normalizePolygonItem(item, {
      name: "地块红线",
      stroke: "#e1262f",
      fill: "#f8ed9a"
    }, "parcel", index));

    const stationOutlineSeed = Array.isArray(input.stationOutlines)
      ? input.stationOutlines
      : (input.station?.body || input.station?.path ? [{
          ...(input.station || {}),
          path: input.station.body || input.station.path
        }] : []);
    geometry.stationOutlines = stationOutlineSeed.map((item, index) => normalizePolygonItem(item, {
      name: "站体",
      stroke: "#7d3f98",
      fill: "#8a58a5"
    }, "station", index));

    const exitSeed = Array.isArray(input.exits)
      ? input.exits
      : (input.station?.exitPoint ? [{
          id: "exit-1",
          name: input.station.exitName || "1号口",
          point: input.station.exitPoint,
          stationOutlineId: geometry.stationOutlines[0]?.id || ""
        }] : []);
    geometry.exits = exitSeed.map((item, index) => ({
      ...item,
      id: stableId(item, "exit", index),
      name: item.name || `出口 ${index + 1}`,
      point: clonePoint(item.point || item.position || item.exitPoint),
      stationOutlineId: item.stationOutlineId || geometry.stationOutlines[0]?.id || ""
    })).filter((item) => item.point);

    const channelSeed = Array.isArray(input.channels)
      ? input.channels
      : (input.channel ? [input.channel] : []);
    geometry.channels = normalizeSpatialCollection(channelSeed, {
      name: "通道",
      stroke: "#0b77bd",
      fill: "#1d8ccf",
      spaceType: "underground",
      groundFloors: 0,
      undergroundFloors: 1
    }, "channel");

    const buildingSeed = Array.isArray(input.buildings)
      ? input.buildings
      : (input.proposedBuilding?.path ? [input.proposedBuilding] : []);
    geometry.buildings = normalizeSpatialCollection(buildingSeed, {
      name: "建筑",
      stroke: "#111827",
      fill: "#ffffff",
      spaceType: "ground",
      groundFloors: 4,
      undergroundFloors: 1
    }, "building");

    const spatialSeed = Array.isArray(input.spatialItems)
      ? input.spatialItems
      : (input.underground?.path ? [{
          ...(input.underground || {}),
          id: "space-underground-1",
          name: input.underground.name || "地下空间",
          spaceType: "underground",
          groundFloors: 0,
          undergroundFloors: 1
        }] : []);
    geometry.spatialItems = normalizeSpatialCollection(spatialSeed, {
      name: "空间",
      stroke: "#176bd6",
      fill: "#ffffff",
      spaceType: "underground",
      groundFloors: 0,
      undergroundFloors: 1
    }, "space");

    const selectedChannel = geometry.channels.find((item) => item.id === input.selectedChannelId) || firstWithGeometry(geometry.channels);
    geometry.selectedChannelId = selectedChannel?.id || "";
    geometry.channel = selectedChannel ? { ...selectedChannel } : normalizeSpatialItem(input.channel || {}, {
      spaceType: "underground",
      groundFloors: 0,
      undergroundFloors: 1
    });

    const selectedBuilding = geometry.buildings.find((item) => item.id === input.selectedBuildingId) || firstWithGeometry(geometry.buildings);
    geometry.selectedBuildingId = selectedBuilding?.id || "";
    geometry.proposedBuilding = selectedBuilding ? { ...selectedBuilding } : {
      ...(input.proposedBuilding || {}),
      path: clonePath(input.proposedBuilding?.path)
    };

    geometry.parcel = geometry.parcels[0] ? { ...geometry.parcels[0] } : normalizePolygonItem(input.parcel || {}, {
      name: "地块红线",
      stroke: "#e1262f",
      fill: "#f8ed9a"
    }, "parcel", 0);

    const firstStation = geometry.stationOutlines[0] || normalizePolygonItem(input.station || {}, {
      name: "站体",
      stroke: "#7d3f98",
      fill: "#8a58a5"
    }, "station", 0);
    const firstExit = geometry.exits[0] || {};
    geometry.station = normalizeSpatialItem({
      ...(input.station || {}),
      ...firstStation,
      body: clonePath(firstStation.path),
      path: clonePath(firstStation.path),
      exitName: firstExit.name || input.station?.exitName || "1号口",
      exitPoint: firstExit.point || clonePoint(input.station?.exitPoint)
    }, {
      spaceType: "underground",
      groundFloors: 0,
      undergroundFloors: 2
    });

    geometry.underground = geometry.spatialItems.find((item) => item.spaceType === "underground") || {
      ...(input.underground || {}),
      path: clonePath(input.underground?.path)
    };

    return geometry;
  }

  function spaceTypeLabel(value) {
    return normalizeSpaceType(value) === "underground" ? "地下" : "地上";
  }

  function floorSummary(item = {}) {
    const normalized = normalizeSpatialItem(item);
    return `地上${normalized.groundFloors}层 / 地下${normalized.undergroundFloors}层`;
  }

  function volumeProjection({ spaceType, angleDegrees = -58, height = 44 } = {}) {
    const kind = normalizeSpaceType(spaceType);
    const radians = (Number(angleDegrees) * Math.PI) / 180;
    const magnitude = Math.max(8, Math.min(96, Number(height) || 44));
    const offsetX = Math.cos(radians) * magnitude;
    const offsetY = Math.abs(Math.sin(radians) * magnitude) * (kind === "underground" ? 1 : -1);
    return {
      kind,
      dashed: kind === "underground",
      offsetX,
      offsetY
    };
  }

  return {
    GEOMETRY_SCHEMA_VERSION,
    MAX_GROUND_FLOORS,
    normalizeSpaceType,
    normalizeSpatialItem,
    normalizeGeometryV2,
    spaceTypeLabel,
    floorSummary,
    volumeProjection
  };
});
