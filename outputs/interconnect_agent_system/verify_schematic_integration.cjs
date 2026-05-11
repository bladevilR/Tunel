const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const root = __dirname;
const url = process.env.INTERCONNECT_URL || "http://127.0.0.1:8765/";
const schematicUrl = new URL("/schematic/index.html", url).toString();
const screenshotPath = path.join(root, "schematic-integration-20260508.png");

function browserExecutable() {
  return [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean).find((item) => fs.existsSync(item));
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  await fsp.rm(path.join(root, "frontend", "schematic", "user_geometry.json"), { force: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable(),
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader"]
  });
  const context = await browser.newContext({ viewport: { width: 1700, height: 940 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => errors.push(error.message || String(error)));
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    if (!request.url().includes("favicon.ico")) {
      failedRequests.push({ url: request.url(), errorText: failure ? failure.errorText : "unknown" });
    }
  });

  await page.goto(url, { waitUntil: "load", timeout: 30000 });
  await page.waitForSelector("#schematicNavLink", { timeout: 10000 });
  const navText = await page.locator("#schematicNavLink").innerText();
  assert(navText.includes("示意图"), "main navigation should expose schematic page");

  const html = await (await context.request.get(schematicUrl)).text();
  assert(!html.includes("__AMAP_JS_KEY__"), "AMap key placeholder should be injected on integrated schematic page");

  await page.goto(`${schematicUrl}?verifyIntegrated=${Date.now()}`, { waitUntil: "load", timeout: 45000 });
  await page.waitForFunction(() => document.body.dataset.ready === "true", null, { timeout: 45000 });
  await page.waitForTimeout(900);

  const controls = await page.evaluate(() => ({
    customModel: Boolean(document.querySelector("#customModelToggle")),
    perspective: Boolean(document.querySelector("#perspectiveDragButton")),
    buildingSelect: Boolean(document.querySelector("#buildingSelect")),
    autoChannel: Boolean(document.querySelector("#autoChannelButton")),
    summary: window.__AMAP_SYNC__?.getSummary()
  }));
  assert(controls.customModel && controls.perspective && controls.buildingSelect && controls.autoChannel, "schematic controls missing");
  assert(controls.summary && controls.summary.useCustomBuildingPrisms === false, "custom building prisms should be off by default");

  const box = await page.locator("#map2d").boundingBox();
  assert(box, "2D map box missing");
  const clickPoint = async (rx, ry) => page.mouse.click(box.x + box.width * rx, box.y + box.height * ry);
  async function drawTool(tool, points) {
    await page.locator(`[data-draw-tool="${tool}"]`).click();
    for (const [rx, ry] of points) {
      await clickPoint(rx, ry);
      await page.waitForTimeout(80);
    }
    if (tool !== "exit") {
      await page.locator("#finishDrawButton").click();
      await page.waitForTimeout(260);
    }
  }

  await drawTool("building", [[0.36, 0.34], [0.46, 0.34], [0.46, 0.45], [0.36, 0.45]]);
  await drawTool("building", [[0.58, 0.48], [0.70, 0.48], [0.70, 0.60], [0.58, 0.60]]);
  await page.locator("#customModelToggle").click();
  await page.evaluate(() => window.__AMAP_SYNC__.setModelPerspective(-24, 62));
  await page.locator('[data-draw-tool="exit"]').click();
  await clickPoint(0.82, 0.38);
  await page.waitForTimeout(250);
  await page.locator("#autoChannelButton").click();
  await page.waitForTimeout(350);
  await page.evaluate(() => window.__AMAP_SYNC__.saveUserGeometry());

  const state = await page.evaluate(() => ({
    summary: window.__AMAP_SYNC__.getSummary(),
    channelCenterline: window.__AMAP_SYNC__.geometry.channel.centerline.length,
    channelFootprint: window.__AMAP_SYNC__.geometry.channel.path.length,
    selectOptions: Array.from(document.querySelector("#buildingSelect").options).map((option) => option.textContent)
  }));
  assert(state.summary.buildingCount === 2, `expected 2 buildings, got ${state.summary.buildingCount}`);
  assert(state.summary.useCustomBuildingPrisms === true, "custom model toggle should work");
  assert(Math.round(state.summary.modelExtrudeAngle) === -24, "manual perspective angle should be settable");
  assert(state.channelCenterline >= 3 && state.channelFootprint >= 6, "auto channel should generate centerline and footprint");
  assert(state.selectOptions.length === 2, "building select should list multiple buildings");
  assert(errors.length === 0, `page errors: ${errors.join("; ")}`);

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await context.close();
  await browser.close();

  const saved = JSON.parse(fs.readFileSync(path.join(root, "frontend", "schematic", "user_geometry.json"), "utf-8"));
  assert(saved.buildings.length === 2, "integrated schematic save should persist buildings");
  console.log(JSON.stringify({ ok: true, schematicUrl, screenshotPath, failedRequests: failedRequests.slice(0, 8) }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
