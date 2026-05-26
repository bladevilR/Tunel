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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1 });
  await page.goto(new URL("/#assessment", url).toString(), { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll("#stationList option").length > 4, null, { timeout: 15000 });

  const stations = await page.evaluate(() => {
    const options = Array.from(document.querySelectorAll("#stationList option"));
    const lineOf = (option) => String(option.label || "").split("/").slice(1).join("/").trim();
    const transfer = options.find((option) => option.value && lineOf(option).includes("/"));
    const normal = options.find((option) => option.value && lineOf(option) && !lineOf(option).includes("/") && !lineOf(option).includes("待补齐"));
    return [transfer, normal].map((option) => ({
      name: option.value,
      label: option.label,
      line: lineOf(option)
    }));
  });
  assert(stations[0]?.name && stations[1]?.name, "need two station options with different preset data");

  await page.locator('[name="station.name"]').fill(stations[0].name.slice(0, 1));
  await page.waitForSelector("#stationSearchResults [data-station-name]", { timeout: 10000 });
  const sourceText = await page.locator("#stationSearchResults .station-suggestion small").first().textContent();
  assert(sourceText && sourceText.trim(), "station suggestions should show source labels");
  const clickedName = await page.locator("#stationSearchResults [data-station-name]").first().getAttribute("data-station-name");
  await page.locator("#stationSearchResults [data-station-name]").first().click();
  await page.waitForFunction((expected) => document.querySelector('[name="station.name"]').value === expected, clickedName);

  await page.locator('[name="station.name"]').fill(stations[0].name);
  await page.locator('[name="station.name"]').dispatchEvent("change");
  await page.waitForFunction((expected) => {
    return document.querySelector('[name="station.line"]').value === expected;
  }, stations[0].line);
  const firstLine = await page.locator('[name="station.line"]').inputValue();
  const firstType = await page.locator('[name="station.stationType"]').inputValue();
  assert(firstLine, "first station should autofill line");
  assert(firstType === "current_transfer", "transfer station should autofill current transfer station type");

  await page.locator('[name="station.name"]').fill(stations[1].name);
  await page.locator('[name="station.name"]').dispatchEvent("change");
  await page.waitForFunction((expected) => {
    return document.querySelector('[name="station.line"]').value === expected;
  }, stations[1].line);
  const secondLine = await page.locator('[name="station.line"]').inputValue();
  const secondType = await page.locator('[name="station.stationType"]').inputValue();
  assert(secondLine && secondLine !== firstLine, "changing station should refresh autofilled line");
  assert(secondType === "normal", "normal station should autofill normal station type");

  await page.locator('[name="station.line"]').fill("人工指定线路");
  await page.locator('[name="station.line"]').dispatchEvent("input");
  await page.locator('[name="station.stationType"]').selectOption("planned_transfer");
  await page.locator('[name="station.stationType"]').dispatchEvent("change");
  await page.locator('[name="station.name"]').fill(stations[0].name);
  await page.locator('[name="station.name"]').dispatchEvent("change");
  await page.waitForTimeout(300);
  const manualLine = await page.locator('[name="station.line"]').inputValue();
  const manualType = await page.locator('[name="station.stationType"]').inputValue();
  assert(manualLine === "人工指定线路", "manual station line edit should not be overwritten");
  assert(manualType === "planned_transfer", "manual station type edit should not be overwritten");

  await browser.close();
  console.log(JSON.stringify({ ok: true, stations, firstLine, secondLine }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
