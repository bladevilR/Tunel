const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
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

async function assertOkResponse(response, label) {
  const data = await response.json();
  assert.equal(data.ok, true, `${label}: ${JSON.stringify(data)}`);
  return data;
}

async function verifyWorkbench(page) {
  await page.goto(new URL("/#assessment", url).toString(), { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll("#stationList option").length > 4, null, { timeout: 15000 });

  const stationName = await page.locator("#stationList option").first().getAttribute("value");
  assert.ok(stationName, "station fixture should be available");
  await page.locator('[name="name"]').fill("Core Browser Flow Project");
  await page.locator('[name="projectCode"]').fill("CORE-BROWSER-001");
  await page.locator('[name="station.name"]').fill(String(stationName).slice(0, 1));
  await page.waitForSelector("#stationSearchResults [data-station-name]", { timeout: 10000 });
  await page.locator("#stationSearchResults [data-station-name]").first().click();
  await page.waitForFunction(() => document.querySelector('[name="station.line"]').value.trim().length > 0);

  const [intakeDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.locator("#exportProjectIntakeBtn").click()
  ]);
  const intakePath = await intakeDownload.path();
  const intake = JSON.parse(fs.readFileSync(intakePath, "utf8"));
  assert.equal(intake.schemaVersion, "interconnect.project-intake.v1");

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "interconnect-core-browser-"));
  const importPath = path.join(tmpDir, "project-intake.json");
  fs.writeFileSync(importPath, JSON.stringify({
    schemaVersion: "interconnect.project-intake.v1",
    record: {
      project: {
        name: "Imported Core Browser Project",
        projectCode: "CORE-BROWSER-IMPORT",
        station: { name: stationName }
      }
    }
  }), "utf8");
  await page.locator("#importProjectIntakeFile").setInputFiles(importPath);
  await page.waitForFunction(() => document.querySelector('[name="name"]').value === "Imported Core Browser Project");

  await Promise.all([
    page.waitForFunction(() => document.querySelector("#reportPreview .report-document"), null, { timeout: 60000 }),
    page.locator("#evaluateBtn").click()
  ]);
  const [reportDownload] = await Promise.all([
    page.waitForEvent("download", { timeout: 60000 }),
    page.locator("#exportBtn").click()
  ]);
  const reportPath = await reportDownload.path();
  assert.ok(reportPath && fs.statSync(reportPath).size > 0, "report export download should be non-empty");
  const reportLinks = await page.$$eval("#exportFiles a", (links) => links.map((link) => link.getAttribute("href")));
  assert.ok(reportLinks.length >= 2, "report export should render multiple download links");
  assert.ok(reportLinks.every((href) => href && href.startsWith("/exports/")), "report links should be served URLs");
}

async function verifySchematic(page) {
  await page.goto(new URL("/schematic/index.html", url).toString(), { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector("#exportPngButton", { timeout: 10000 });
  const result = await page.evaluate(async () => {
    let originalGeometry = null;
    try {
      const originalResponse = await fetch("/api/schematic/user-geometry", { cache: "no-store" });
      const originalPayload = await originalResponse.json();
      if (originalPayload && originalPayload.ok !== false && originalPayload.parcel) {
        originalGeometry = originalPayload;
      }
    } catch (_error) {
      originalGeometry = null;
    }
    const geometry = {
      meta: { version: "schematic-geometry.v2", center: [120.62, 31.31], savedBy: "verify_core_browser_flows" },
      parcel: { path: [[120.6200, 31.3100], [120.6206, 31.3100], [120.6206, 31.3105], [120.6200, 31.3105]] },
      parcels: [
        { id: "parcel-browser-flow", name: "Browser flow parcel", path: [[120.6200, 31.3100], [120.6206, 31.3100], [120.6206, 31.3105], [120.6200, 31.3105]] }
      ],
      stationOutlines: [
        { id: "station-browser-flow", name: "Browser flow station", path: [[120.6209, 31.3100], [120.6213, 31.3100], [120.6213, 31.3103], [120.6209, 31.3103]] }
      ],
      channels: [
        { id: "channel-browser-flow", name: "Browser flow channel", path: [[120.6206, 31.3102], [120.6209, 31.3102]] }
      ],
      spatialItems: [
        {
          id: "space-browser-flow",
          name: "Browser flow space",
          spaceType: "ground",
          groundFloors: 6,
          undergroundFloors: 1,
          path: [[120.6201, 31.3101], [120.6204, 31.3101], [120.6204, 31.3104], [120.6201, 31.3104]]
        }
      ],
      exits: [],
      labels: [],
      viewState: { pitch: 55, rotation: 25, zoom: 17, center: [120.6205, 31.3102] }
    };
    try {
      const saveResponse = await fetch("/api/schematic/user-geometry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(geometry)
      });
      const save = await saveResponse.json();
      const exportResponse = await fetch("/api/schematic/export-png", { method: "POST" });
      const exported = await exportResponse.json();
      return { saveStatus: saveResponse.status, save, exportStatus: exportResponse.status, exported };
    } finally {
      if (originalGeometry) {
        await fetch("/api/schematic/user-geometry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(originalGeometry)
        });
      }
    }
  });
  assert.equal(result.saveStatus, 200, JSON.stringify(result));
  assert.equal(result.save.ok, true, JSON.stringify(result));
  assert.equal(result.exportStatus, 200, JSON.stringify(result));
  assert.equal(result.exported.ok, true, JSON.stringify(result));
  assert.equal(result.exported.export.contentType, "image/png");
  assert.ok(result.exported.export.downloadUrl.startsWith("/schematic/exports/"), "PNG should expose served download URL");
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1, acceptDownloads: true });
    await verifyWorkbench(page);
    await verifySchematic(page);
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ ok: true }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
