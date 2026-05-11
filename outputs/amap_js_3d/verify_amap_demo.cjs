const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = __dirname;
const url = process.env.AMAP_DEMO_URL || "http://127.0.0.1:8899/amap_3d_demo.html";
const screenshotPath = path.join(root, "amap_3d_demo_screenshot.png");
const resultPath = path.join(root, "amap_3d_demo_verify.json");

function resolveBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);

  return candidates.find((candidate) => fsSync.existsSync(candidate));
}

async function main() {
  const executablePath = resolveBrowserExecutable();
  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader"]
  });

  const page = await browser.newPage({
    viewport: { width: 1600, height: 960 },
    deviceScaleFactor: 1
  });

  const logs = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on("console", (message) => {
    logs.push({ type: message.type(), text: message.text() });
  });
  page.on("pageerror", (error) => {
    pageErrors.push(String(error && error.message ? error.message : error));
  });
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    failedRequests.push({
      url: request.url(),
      errorText: failure ? failure.errorText : "unknown"
    });
  });

  await page.goto(url, { waitUntil: "load", timeout: 45000 });
  await page.waitForFunction(
    () => document.body.dataset.ready === "true" || document.body.dataset.ready === "failed",
    null,
    { timeout: 45000 }
  );
  await page.waitForTimeout(2500);

  const statusText = await page.locator("#status").innerText({ timeout: 5000 });
  const readyState = await page.evaluate(() => document.body.dataset.ready || "");
  const mapSummary = await page.evaluate(() => {
    const map = window.__AMAP_DEMO_MAP__;
    const center = map && map.getCenter ? map.getCenter() : null;
    return {
      hasAmap: Boolean(window.AMap),
      hasMap: Boolean(map),
      hasOverlay3d: document.body.dataset.overlay3d === "true",
      hasObject3DPrism: Boolean(window.AMap && AMap.Object3D && AMap.Object3D.Prism),
      hasObject3DLayer: Boolean(window.AMap && AMap.Object3DLayer),
      center: center ? [center.lng, center.lat] : null,
      zoom: map && map.getZoom ? map.getZoom() : null,
      pitch: map && map.getPitch ? map.getPitch() : null,
      rotation: map && map.getRotation ? map.getRotation() : null
    };
  });

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await browser.close();

  const result = {
    ok: readyState === "true" && mapSummary.hasAmap && mapSummary.hasMap,
    url,
    readyState,
    statusText,
    mapSummary,
    pageErrors,
    failedRequests: failedRequests.filter((item) => !item.url.includes("favicon.ico")).slice(0, 20),
    recentLogs: logs.slice(-30),
    screenshotPath
  };

  await fs.writeFile(resultPath, JSON.stringify(result, null, 2), "utf-8");
  console.log(JSON.stringify(result, null, 2));

  if (!result.ok || pageErrors.length > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
