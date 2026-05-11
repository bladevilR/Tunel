const fsSync = require("node:fs");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

function browserPath() {
  return [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean).find((item) => fsSync.existsSync(item));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

(async () => {
  await fs.rm(path.join(__dirname, "user_geometry.json"), { force: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserPath(),
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader"]
  });
  const page = await browser.newPage({ viewport: { width: 1700, height: 920 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:8898/index.html?verifyV2=${Date.now()}`, {
    waitUntil: "load",
    timeout: 45000
  });
  await page.waitForFunction(() => document.body.dataset.ready === "true", null, { timeout: 45000 });
  await page.waitForTimeout(800);

  const controls = await page.evaluate(() => ({
    buildingSelect: Boolean(document.querySelector("#buildingSelect")),
    autoChannel: Boolean(document.querySelector("#autoChannelButton")),
    customModel: Boolean(document.querySelector("#customModelToggle")),
    perspective: Boolean(document.querySelector("#perspectiveDragButton")),
    buildingSummary: window.__AMAP_SYNC__?.getSummary().buildingCount
  }));
  assert(controls.buildingSelect, "missing building select");
  assert(controls.autoChannel, "missing auto channel button");
  assert(controls.customModel, "missing custom model toggle");
  assert(controls.perspective, "missing perspective drag button");
  assert(controls.buildingSummary === 0, "building count should start at 0");

  const box = await page.locator("#map2d").boundingBox();
  assert(box, "map2d box missing");
  const clickPoint = async (rx, ry) => page.mouse.click(box.x + box.width * rx, box.y + box.height * ry);
  async function drawTool(tool, points) {
    await page.locator(`[data-draw-tool="${tool}"]`).click();
    for (const [rx, ry] of points) {
      await clickPoint(rx, ry);
      await page.waitForTimeout(80);
    }
    await page.locator("#finishDrawButton").click();
    await page.waitForTimeout(300);
  }

  await drawTool("building", [[0.36, 0.34], [0.46, 0.34], [0.46, 0.45], [0.36, 0.45]]);
  await drawTool("building", [[0.58, 0.48], [0.70, 0.48], [0.70, 0.60], [0.58, 0.60]]);
  let state = await page.evaluate(() => ({
    buildingCount: window.__AMAP_SYNC__.getSummary().buildingCount,
    selectedBuildingId: window.__AMAP_SYNC__.getSummary().selectedBuildingId,
    selectOptions: Array.from(document.querySelector("#buildingSelect").options).map((option) => option.textContent),
    labelIds: window.__AMAP_SYNC__.geometry.labels.map((label) => label.id)
  }));
  assert(state.buildingCount === 2, `expected 2 buildings, got ${state.buildingCount}`);
  assert(state.selectOptions.length === 2, "building select should list 2 buildings");
  assert(state.labelIds.includes("building-1") && state.labelIds.includes("building-2"), "building labels should be per-building");

  const beforePerspective = await page.evaluate(() => window.__AMAP_SYNC__.getSummary());
  await page.locator("#customModelToggle").click();
  await page.evaluate(() => window.__AMAP_SYNC__.setModelPerspective(-20, 60));
  await page.waitForTimeout(300);
  const afterPerspective = await page.evaluate(() => {
    const selected = window.__AMAP_SYNC__.getSelectedBuilding();
    const summary = window.__AMAP_SYNC__.getSummary();
    return { id: selected.id, path: selected.path.map((point) => point.slice()), summary };
  });
  assert(afterPerspective.summary.useCustomBuildingPrisms === true, "custom model toggle should enable optional custom prisms");
  assert(afterPerspective.summary.modelExtrudeAngle !== beforePerspective.modelExtrudeAngle, "perspective angle should change");
  assert(afterPerspective.summary.modelExtrudeHeight !== beforePerspective.modelExtrudeHeight, "perspective height should change");

  await page.locator('[data-draw-tool="exit"]').click();
  await clickPoint(0.82, 0.38);
  await page.waitForTimeout(250);
  await page.locator("#autoChannelButton").click();
  await page.waitForTimeout(350);
  state = await page.evaluate(() => ({
    channelCenterline: window.__AMAP_SYNC__.geometry.channel.centerline.map((point) => point.slice()),
    channelFootprintLength: window.__AMAP_SYNC__.geometry.channel.path.length,
    selectedBuildingId: window.__AMAP_SYNC__.getSummary().selectedBuildingId,
    guide: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(state.channelCenterline.length >= 3, "auto channel should create a centerline with an intermediate bend");
  assert(state.channelFootprintLength >= 6, "auto channel should create a footprint");
  assert(state.guide.includes("通道"), "guide should mention generated channel");

  await browser.close();
  console.log(JSON.stringify({ ok: true }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
