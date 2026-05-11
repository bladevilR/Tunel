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
  const page = await browser.newPage({ viewport: { width: 1500, height: 850 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:8898/index.html?verifyWorkflow=${Date.now()}`, {
    waitUntil: "load",
    timeout: 45000
  });
  await page.waitForFunction(() => document.body.dataset.ready === "true", null, { timeout: 45000 });
  await page.waitForTimeout(800);

  const hasWorkflowControls = await page.evaluate(() => ({
    undo: Boolean(document.querySelector("#undoDrawButton")),
    cancel: Boolean(document.querySelector("#cancelDrawButton")),
    clear: Boolean(document.querySelector("#clearLayerButton")),
    toggle: Boolean(document.querySelector("#toggleGuideButton")),
    guide: Boolean(document.querySelector("#workflowGuide")),
    guideText: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(hasWorkflowControls.undo, "missing undo drawing button");
  assert(hasWorkflowControls.cancel, "missing cancel drawing button");
  assert(hasWorkflowControls.clear, "missing clear layer button");
  assert(hasWorkflowControls.toggle, "missing guide toggle button");
  assert(hasWorkflowControls.guide, "missing workflow guide");

  let panelState = await page.evaluate(() => {
    const panel = document.querySelector("#drawPanel");
    const rect = panel.getBoundingClientRect();
    return {
      collapsed: panel.classList.contains("is-collapsed"),
      width: rect.width,
      height: rect.height,
      expanded: document.querySelector("#toggleGuideButton")?.getAttribute("aria-expanded")
    };
  });
  assert(panelState.collapsed, "guide panel should be collapsed by default");
  assert(panelState.width <= 90 && panelState.height <= 48, `collapsed guide is too large: ${panelState.width}x${panelState.height}`);
  assert(panelState.expanded === "false", "guide toggle should report collapsed state");

  await page.locator("#toggleGuideButton").click();
  panelState = await page.evaluate(() => {
    const panel = document.querySelector("#drawPanel");
    const rect = panel.getBoundingClientRect();
    return {
      collapsed: panel.classList.contains("is-collapsed"),
      width: rect.width,
      height: rect.height,
      expanded: document.querySelector("#toggleGuideButton")?.getAttribute("aria-expanded")
    };
  });
  assert(!panelState.collapsed, "guide panel should expand when toggled");
  assert(panelState.expanded === "true", "guide toggle should report expanded state");
  await page.locator("#toggleGuideButton").click();

  await page.locator('[data-draw-tool="parcel"]').click();
  const box = await page.locator("#map2d").boundingBox();
  assert(box, "map2d box missing");
  const clickPoint = async (rx, ry) => page.mouse.click(box.x + box.width * rx, box.y + box.height * ry);

  await clickPoint(0.30, 0.32);
  await clickPoint(0.48, 0.32);
  await clickPoint(0.44, 0.50);
  let state = await page.evaluate(() => ({
    drawingPoints: window.__AMAP_SYNC_LAST_DRAW__?.pathLength || 0,
    undoDisabled: document.querySelector("#undoDrawButton")?.disabled,
    guide: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(state.drawingPoints === 3, `expected 3 drawing points, got ${state.drawingPoints}`);
  assert(state.undoDisabled === false, "undo button should be enabled after points are added");
  assert(state.guide.includes("3"), "workflow guide should reflect point count");

  await page.locator("#undoDrawButton").click();
  state = await page.evaluate(() => ({
    drawingPoints: window.__AMAP_SYNC_LAST_DRAW__?.pathLength || 0,
    parcelVertices: window.__AMAP_SYNC__.geometry.parcel.path.length,
    guide: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(state.drawingPoints === 2, `expected 2 points after undo, got ${state.drawingPoints}`);
  assert(state.parcelVertices === 0, "undo while drawing should not commit parcel geometry");

  await clickPoint(0.44, 0.50);
  await page.locator("#finishDrawButton").click();
  state = await page.evaluate(() => ({
    drawLocked: window.__AMAP_SYNC__.getSummary().drawLocked,
    parcelVertices: window.__AMAP_SYNC__.geometry.parcel.path.length,
    guide: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(state.drawLocked === false, "draw lock should release after finishing");
  assert(state.parcelVertices === 3, `expected committed parcel with 3 vertices, got ${state.parcelVertices}`);
  assert(state.guide.includes("保存") && state.guide.includes("导出"), "guide should explain next step after finish");

  await page.locator("#clearLayerButton").click();
  state = await page.evaluate(() => ({
    parcelVertices: window.__AMAP_SYNC__.geometry.parcel.path.length,
    guide: document.querySelector("#workflowGuide")?.textContent || ""
  }));
  assert(state.parcelVertices === 0, "clear current layer should remove committed parcel");
  assert(state.guide.includes("已清空"), "guide should confirm clear action");

  await browser.close();
  console.log(JSON.stringify({ ok: true }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
