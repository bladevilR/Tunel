const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const root = __dirname;
const url = process.env.INTERCONNECT_URL || "http://127.0.0.1:8765/";
const screenshotPath = path.join(root, "interconnect_agent_screenshot.png");
const resultPath = path.join(root, "interconnect_agent_verify.json");

function apiUrl(route) {
  return new URL(route, url).toString();
}

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
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable()
  });
  const context = await browser.newContext({
    viewport: { width: 1680, height: 1040 },
    deviceScaleFactor: 1,
    acceptDownloads: true
  });
  await context.addInitScript(() => {
    window.localStorage.setItem("modelLedUiOfflineFallback", "1");
  });
  const page = await context.newPage();
  const logs = [];
  const errors = [];
  const failedRequests = [];

  page.on("console", (message) => logs.push({ type: message.type(), text: message.text() }));
  page.on("pageerror", (error) => errors.push(error.message || String(error)));
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    failedRequests.push({ url: request.url(), errorText: failure ? failure.errorText : "unknown" });
  });

  const sourcesPayload = await (await context.request.get(apiUrl("/api/sources"))).json();
  const exportsPayload = await (await context.request.get(apiUrl("/api/exports"))).json();
  const deliveryManifestPayload = await (await context.request.get(apiUrl("/api/delivery/manifest"))).json();
  const deliveryPackageResponse = await context.request.get(apiUrl("/api/delivery/package"));
  const deliveryPackageBytes = await deliveryPackageResponse.body();
  const demoProject = JSON.parse(fs.readFileSync(path.join(root, "data", "demo_cases.json"), "utf-8")).cases[0];
  const forgedExportResponse = await context.request.post(apiUrl("/api/export"), {
    data: {
      project: demoProject,
      researchOptions: { allowOfflineFallback: true, forceOfflineFallback: true },
      result: {
        project: demoProject,
        score: 9999,
        scorePercent: 999,
        level: "伪造等级",
        recommendation: { primary: { name: "伪造方案" } },
        report: [{ title: "伪造报告", content: "不应进入后端导出文件" }]
      }
    }
  });
  const forgedExportPayload = await forgedExportResponse.json();
  const forgedSnapshotFile = (forgedExportPayload.export?.files || []).find((item) => item.filename.endsWith(".json"));
  const forgedSnapshotPayload = forgedSnapshotFile
    ? JSON.parse(fs.readFileSync(path.join(root, forgedSnapshotFile.relativePath), "utf-8"))
    : {};

  await page.goto(url, { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => {
    return document.querySelectorAll("#stationList option").length > 0
      && document.querySelector("#demoSelect")?.value;
  }, null, { timeout: 15000 });
  await page.click("#evaluateBtn");
  await page.waitForFunction(() => {
    const score = document.querySelector("#scoreValue");
    const level = document.querySelector("#levelValue");
    const type = document.querySelector("#typeValue");
    return score && level && type && score.textContent !== "--" && level.textContent !== "--" && type.textContent !== "--";
  }, null, { timeout: 15000 });

  await page.click("#saveProjectBtn");
  await page.waitForFunction(() => {
    const select = document.querySelector("#projectSelect");
    return select && select.value;
  }, null, { timeout: 10000 });

  const downloadPromise = page.waitForEvent("download", { timeout: 10000 }).catch(() => null);
  await page.click("#exportBtn");
  await downloadPromise;
  await page.waitForFunction(() => {
    return document.querySelectorAll("#exportFiles a").length >= 5;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="dashboard"]');
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "dashboard"
      && document.querySelectorAll("#projectTableBody tr").length >= 1
      && document.querySelectorAll("#completionBacklog .completion-item").length >= 1
      && document.querySelectorAll("#exportHistory .export-row").length >= 1;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="assessment"]');
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "assessment"
      && document.querySelectorAll(".factor-line").length >= 6
      && document.querySelectorAll("#stationContextPanel > div").length >= 5;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="knowledge"]');
  await page.waitForSelector("#knowledgeSearchInput", { timeout: 5000 });
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "knowledge"
      && document.querySelector("#knowledgeSearchInput")
      && document.querySelector("#knowledgeCategoryFilter");
  }, null, { timeout: 10000 });
  await page.fill("#knowledgeSearchInput", "\u91d1\u5bb6\u5830 \u51fa\u5165\u53e3");
  await page.click("#knowledgeSearchBtn");
  await page.waitForFunction(() => {
    return document.querySelectorAll(".knowledge-result").length >= 1;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="reporting"]');
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "reporting"
      && document.querySelectorAll(".report-section").length >= 1
      && document.querySelectorAll("#missingList .completion-item").length >= 1
      && !document.body.innerText.includes("旧版 Word 转换");
  }, null, { timeout: 10000 });

  const summary = await page.evaluate(() => ({
    title: document.title,
    score: document.querySelector("#scoreValue")?.textContent,
    level: document.querySelector("#levelValue")?.textContent,
    type: document.querySelector("#typeValue")?.textContent,
    completeness: document.querySelector("#completenessValue")?.textContent,
    projectCount: document.querySelector("#projectCountValue")?.textContent,
    savedProject: document.querySelector("#projectSelect")?.selectedOptions?.[0]?.textContent,
    exportPath: document.querySelector("#exportPathValue")?.textContent,
    exportFileCount: document.querySelectorAll("#exportFiles a").length,
    sectionCount: document.querySelectorAll(".report-section").length,
    dimensionCount: document.querySelectorAll(".dimension-row").length,
    knowledgeSourceCount: document.querySelector("#knowledgeSourceCount")?.textContent,
    knowledgeChunkCount: document.querySelector("#knowledgeChunkCount")?.textContent,
    knowledgeResultCount: document.querySelectorAll(".knowledge-result").length,
    backlogCount: document.querySelectorAll("#completionBacklog .completion-item").length,
    exportHistoryCount: document.querySelectorAll("#exportHistory .export-row").length,
    activeView: document.querySelector(".view.active")?.id,
    legacyWordGapVisible: document.body.innerText.includes("旧版 Word 转换"),
    hasRecommendation: !document.querySelector("#recommendationBody")?.classList.contains("empty-state")
  }));

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await context.close();
  await browser.close();

  const result = {
    ok: summary.sectionCount >= 1
      && summary.dimensionCount === 4
      && summary.hasRecommendation
      && !summary.legacyWordGapVisible
      && Boolean(summary.savedProject)
      && summary.exportFileCount >= 5
      && summary.knowledgeResultCount >= 1
      && summary.backlogCount >= 1
      && summary.exportHistoryCount >= 1
      && sourcesPayload.ok
      && sourcesPayload.sources.length >= 21
      && exportsPayload.ok
      && exportsPayload.exports.length >= 1
      && deliveryManifestPayload.ok
      && deliveryManifestPayload.files.length >= 10
      && deliveryManifestPayload.groups.some((group) => group.id === "docs" && group.files.length >= 3)
      && deliveryManifestPayload.package.downloadUrl === "/api/delivery/package"
      && deliveryPackageResponse.ok()
      && deliveryPackageResponse.headers()["content-type"] === "application/zip"
      && deliveryPackageBytes.length > 1024
      && deliveryPackageBytes[0] === 0x50
      && deliveryPackageBytes[1] === 0x4b
      && forgedExportResponse.ok()
      && forgedExportPayload.ok
      && forgedSnapshotPayload.scorePercent !== 999
      && forgedSnapshotPayload.level !== "伪造等级"
      && (forgedSnapshotPayload.recommendation?.primary?.name || "") !== "伪造方案"
      && errors.length === 0,
    url,
    summary,
    apiChecks: {
      sources: { ok: sourcesPayload.ok, count: sourcesPayload.sources.length, unparsed: sourcesPayload.unparsedSources.length },
      exports: { ok: exportsPayload.ok, count: exportsPayload.exports.length },
      deliveryManifest: {
        ok: deliveryManifestPayload.ok,
        totalFiles: deliveryManifestPayload.totalFiles,
        totalSize: deliveryManifestPayload.totalSize,
        groups: deliveryManifestPayload.groups.map((group) => ({ id: group.id, count: group.files.length }))
      },
      deliveryPackage: {
        ok: deliveryPackageResponse.ok(),
        contentType: deliveryPackageResponse.headers()["content-type"],
        size: deliveryPackageBytes.length,
        signature: Array.from(deliveryPackageBytes.slice(0, 2)).map((byte) => byte.toString(16)).join("")
      },
      exportHardening: {
        ok: forgedExportResponse.ok() && forgedExportPayload.ok,
        scorePercent: forgedSnapshotPayload.scorePercent,
        level: forgedSnapshotPayload.level,
        primary: forgedSnapshotPayload.recommendation?.primary?.name || "",
        ignoredForgedResult: forgedSnapshotPayload.scorePercent !== 999
          && forgedSnapshotPayload.level !== "伪造等级"
          && (forgedSnapshotPayload.recommendation?.primary?.name || "") !== "伪造方案"
      }
    },
    errors,
    failedRequests,
    recentLogs: logs.slice(-20),
    screenshotPath
  };
  await fsp.writeFile(resultPath, JSON.stringify(result, null, 2), "utf-8");
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
