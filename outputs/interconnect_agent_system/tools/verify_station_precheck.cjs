const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const projectsPath = path.join(root, "data", "projects.json");
const payload = JSON.parse(fs.readFileSync(projectsPath, "utf8"));
const projects = payload.projects || [];

function fail(message, detail = {}) {
  console.error(JSON.stringify({ ok: false, message, detail }, null, 2));
  process.exit(1);
}

function factorMessages(record) {
  const missing = record.result?.missing || [];
  return Object.fromEntries(missing.map((item) => [item.factorId, item.message]));
}

if (projects.length !== 240) {
  fail("项目库应保持 240 个站点级预评估项目", { count: projects.length });
}

const nonStationRecords = projects.filter((record) => record.batchSeed !== "stations-240" || !String(record.id || "").startsWith("station-"));
if (nonStationRecords.length) {
  fail("项目库应为纯站点级预评估项目，不应混入示例或人工保存项目", {
    records: nonStationRecords.map((record) => ({ id: record.id, name: record.project?.name }))
  });
}

const typeCounts = {};
const missingCombos = {};
for (const record of projects) {
  const primary = record.result?.recommendation?.primary?.name || "";
  typeCounts[primary] = (typeCounts[primary] || 0) + 1;
  const combo = (record.result?.missing || []).map((item) => item.factorId).sort().join(",");
  missingCombos[combo] = (missingCombos[combo] || 0) + 1;
}

if (Object.keys(typeCounts).length < 4) {
  fail("站点预评估推荐不应退化为单一推荐类型", { typeCounts });
}

const expectedRequiredCombo = "development_intensity,land_use,underground_space";
const expectedMissingCombos = {
  [expectedRequiredCombo]: 234,
  "development_intensity,land_use,ridership,underground_space": 6
};
for (const [combo, count] of Object.entries(expectedMissingCombos)) {
  if (missingCombos[combo] !== count) {
    fail("项目库缺项分布应稳定反映正式地块资料缺口", { missingCombos, expectedMissingCombos });
  }
}
if (Object.keys(missingCombos).length !== Object.keys(expectedMissingCombos).length) {
  fail("项目库存在未预期的缺项组合", { missingCombos, expectedMissingCombos });
}

const leqiao = projects.find((item) => item.id === "station-乐桥");
if (!leqiao) {
  fail("缺少乐桥站点预评估项目");
}

const leqiaoPrimary = leqiao.result?.recommendation?.primary?.name;
if (leqiaoPrimary !== "地下主通道") {
  fail("乐桥应基于城市级 TOD、换乘和高客流命中地下主通道预评估规则", { leqiaoPrimary });
}

const messages = factorMessages(leqiao);
for (const factorId of ["land_use", "development_intensity", "underground_space"]) {
  if (!messages[factorId]) {
    fail("乐桥三项地块正式资料缺口应全部保留", { missing: messages });
  }
}

if (!messages.land_use.includes("周边配套") || !messages.underground_space.includes("联通形式")) {
  fail("缺项说明应区分正式缺口与已有站点/运营线索", { messages });
}

console.log(JSON.stringify({
  ok: true,
  count: projects.length,
  typeCounts,
  missingCombos,
  leqiao: {
    primary: leqiaoPrimary,
    rule: leqiao.result?.recommendation?.rule?.id,
    missing: messages
  }
}, null, 2));
