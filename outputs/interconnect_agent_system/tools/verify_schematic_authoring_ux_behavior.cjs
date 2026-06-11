const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright");

const url = process.env.INTERCONNECT_URL || "http://127.0.0.1:8765/";

function browserExecutable() {
  return [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean).find((item) => fs.existsSync(item));
}

async function assertLayout(page, label) {
  const boxes = await page.evaluate(() => {
    const rectOf = (selector) => {
      const rect = document.querySelector(selector).getBoundingClientRect();
      return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
    };
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      topbar: rectOf(".topbar"),
      drawbar: rectOf(".drawbar"),
      maps: rectOf(".maps")
    };
  });
  assert(boxes.drawbar.left >= -1, `${label}: drawbar should not overflow left`);
  assert(boxes.drawbar.right <= boxes.viewport.width + 1, `${label}: drawbar should not overflow right`);
  assert(boxes.maps.height > 120, `${label}: map area should remain visible`);
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1 });
  await page.goto(new URL("/schematic/index.html", url).toString(), { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector("#toggleDrawbarButton", { timeout: 10000 });
  const drawingRuntime = await page.evaluate(() => {
    const source = document.documentElement.innerHTML;
    return {
      hasPreviewState: source.includes("drawingPreviewPoint") && source.includes("drawingPreviewOverlay"),
      hasMouseFollowPreview: source.includes('"pointermove", "mousemove", "touchmove"')
        && source.includes("updateDrawingPreviewOverlay(state")
        && source.includes("drawingPointerStart && Math.hypot")
    };
  });
  assert.equal(drawingRuntime.hasPreviewState, true, "browser-loaded schematic should keep preview overlay state");
  assert.equal(drawingRuntime.hasMouseFollowPreview, true, "browser-loaded schematic should update preview on mouse movement after first click");
  await assertLayout(page, "desktop");

  const visibleBefore = await page.locator(".drawbar button:visible").count();
  assert(visibleBefore > 4, "drawbar should show drawing controls before collapse");
  await page.locator("#toggleDrawbarButton").click();
  await page.waitForFunction(() => document.querySelector(".drawbar").classList.contains("is-collapsed"));
  const visibleAfter = await page.locator(".drawbar button:visible").count();
  assert.equal(visibleAfter, 1, "collapsed drawbar should keep only its toggle visible");

  await page.setViewportSize({ width: 390, height: 860 });
  await page.locator("#toggleDrawbarButton").click();
  await page.waitForFunction(() => !document.querySelector(".drawbar").classList.contains("is-collapsed"));
  await assertLayout(page, "narrow");

  await browser.close();
  console.log(JSON.stringify({ ok: true }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
