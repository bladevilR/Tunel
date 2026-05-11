const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const url = process.env.INTERCONNECT_URL || "http://127.0.0.1:8765/";
const resultPath = path.join(root, "model_led_ui_verify.json");
const screenshotPath = path.join(root, "model_led_ui_verify.png");

function browserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item));
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1040 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message || String(error)));

  await page.goto(url, { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => {
    return document.querySelector("#modelJudgementTitle")
      && document.querySelector("#modelJudgementTitle").textContent.includes("模型");
  }, null, { timeout: 15000 });
  await page.waitForFunction(() => {
    return document.querySelectorAll("#stationList option").length > 0
      && document.querySelector("#demoSelect")?.value;
  }, null, { timeout: 15000 });
  await page.evaluate(() => {
    window.localStorage.setItem("modelLedUiOfflineFallback", "1");
  });
  await page.click("#evaluateBtn");
  await page.waitForFunction(() => {
    return document.querySelector("#modelJudgementTitle")
      && document.querySelector("#modelJudgementTitle").textContent.includes("模型建议");
  }, null, { timeout: 15000 });

  await page.waitForFunction(() => {
    const text = document.body.innerText;
    return text.includes("模型主导研判")
      && text.includes("规则基线")
      && text.includes("复核标签")
      && document.querySelectorAll("#modelRiskList .model-risk-item").length >= 3
      && document.querySelectorAll("#modelFundingList .model-funding-item").length >= 3;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="reporting"]');
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "reporting"
      && document.querySelectorAll("[data-report-mode]").length === 3
      && document.querySelector("#diagramBriefSvg svg");
  }, null, { timeout: 10000 });

  await page.click('[data-report-mode="expert_appendix"]');
  await page.waitForFunction(() => {
    return document.querySelector("[data-report-mode='expert_appendix']").classList.contains("active")
      && document.querySelector("#reportModeSummary").textContent.includes("专家");
  }, null, { timeout: 5000 });

  const summary = await page.evaluate(() => ({
    modelTitle: document.querySelector("#modelJudgementTitle")?.textContent,
    difference: document.querySelector("#modelDifferencePanel")?.textContent,
    risks: document.querySelectorAll("#modelRiskList .model-risk-item").length,
    funding: document.querySelectorAll("#modelFundingList .model-funding-item").length,
    modes: Array.from(document.querySelectorAll("[data-report-mode]")).map((node) => node.textContent.trim()),
    diagramText: document.querySelector("#diagramBriefSvg")?.textContent,
    activeMode: document.querySelector("[data-report-mode].active")?.dataset.reportMode,
  }));

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await context.close();
  await browser.close();

  const result = {
    ok: summary.modelTitle.includes("模型")
      && summary.difference.includes("规则基线")
      && summary.risks >= 3
      && summary.funding >= 3
      && summary.modes.length === 3
      && summary.diagramText.includes("推荐")
      && summary.activeMode === "expert_appendix"
      && errors.length === 0,
    summary,
    errors,
    screenshotPath,
  };
  await fsp.writeFile(resultPath, JSON.stringify(result, null, 2), "utf-8");
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
