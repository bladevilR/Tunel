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

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1, acceptDownloads: true });
  await page.goto(new URL("/#assessment", url).toString(), { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll("#stationList option").length > 4, null, { timeout: 15000 });

  const stationName = await page.locator("#stationList option").first().getAttribute("value");
  assert.ok(stationName, "station fixture should be available");

  await page.locator('[name="name"]').fill("Export Intake Regression Project");
  await page.locator('[name="projectCode"]').fill("INTAKE-REG-001");
  await page.locator('[name="station.name"]').fill(stationName);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.locator("#exportProjectIntakeBtn").click()
  ]);
  const downloadPath = await download.path();
  const exported = JSON.parse(fs.readFileSync(downloadPath, "utf8"));
  assert.equal(exported.schemaVersion, "interconnect.project-intake.v1");
  assert.equal(exported.record.project.name, "Export Intake Regression Project");
  assert.equal(exported.record.project.projectCode, "INTAKE-REG-001");

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "interconnect-intake-"));
  const validPath = path.join(tmpDir, "valid-intake.json");
  fs.writeFileSync(validPath, JSON.stringify({
    schemaVersion: "interconnect.project-intake.v1",
    record: {
      id: "external-intake-record",
      project: {
        name: "Imported Intake Regression Project",
        projectCode: "INTAKE-IMPORT-001",
        station: { name: stationName }
      }
    }
  }), "utf8");

  await page.locator("#importProjectIntakeFile").setInputFiles(validPath);
  await page.waitForFunction(() => document.querySelector('[name="name"]').value === "Imported Intake Regression Project");
  assert.equal(await page.locator('[name="projectCode"]').inputValue(), "INTAKE-IMPORT-001");
  assert.match(await page.locator("#projectIntakeStatus").textContent(), /已导入/);

  const invalidPath = path.join(tmpDir, "invalid-intake.json");
  fs.writeFileSync(invalidPath, JSON.stringify({ schemaVersion: "wrong" }), "utf8");
  await page.locator("#importProjectIntakeFile").setInputFiles(invalidPath);
  await page.waitForFunction(() => /导入失败/.test(document.querySelector("#projectIntakeStatus").textContent));

  await browser.close();
  console.log(JSON.stringify({ ok: true, stationName }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
