const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = __dirname;
const outputDir = path.join(root, "exports");
const timestamp = new Date().toISOString().replace(/[:.]/g, "").slice(0, 15);
const outputPath = path.join(outputDir, `amap-3d-export-${timestamp}.png`);
const url = process.env.AMAP_EXPORT_URL || "http://127.0.0.1:8898/index.html?view=3d&export=1";

function resolveBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: resolveBrowserExecutable(),
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader"]
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 960 },
    deviceScaleFactor: 1
  });

  const pageErrors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => pageErrors.push(String(error && error.message ? error.message : error)));
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
  await page.waitForTimeout(2600);
  await page.screenshot({ path: outputPath, fullPage: true });
  await browser.close();

  const result = {
    ok: pageErrors.length === 0,
    outputPath,
    url,
    pageErrors,
    failedRequests: failedRequests.filter((item) => !item.url.includes("favicon.ico")).slice(0, 12)
  };
  fs.writeFileSync(path.join(root, "last_export.json"), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (!result.ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exit(1);
});
