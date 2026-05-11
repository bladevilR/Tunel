const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

const root = __dirname;
const annotationsPath = path.join(root, "annotations.json");
const annotationsJsPath = path.join(root, "annotations.js");
const htmlPath = path.join(root, "index.html");
const pngPath = path.join(root, "manual_schematic_3d.png");
const verifyPath = path.join(root, "manual_schematic_3d_verify.json");

async function main() {
  const annotations = JSON.parse(fs.readFileSync(annotationsPath, "utf8"));
  fs.writeFileSync(
    annotationsJsPath,
    `window.SCHEMATIC_DATA = ${JSON.stringify(annotations, null, 2)};\n`,
    "utf8"
  );

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (error) {
    if (!String(error.message || error).includes("Executable doesn't exist")) {
      throw error;
    }
    browser = await chromium.launch({ channel: "msedge", headless: true });
  }
  const page = await browser.newPage({
    viewport: {
      width: annotations.canvas.width,
      height: annotations.canvas.height
    },
    deviceScaleFactor: 1
  });

  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      pageErrors.push(message.text());
    }
  });

  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
  await page.waitForFunction(() => window.__SCHEMATIC_READY === true, null, { timeout: 5000 });
  await page.screenshot({ path: pngPath, fullPage: false });
  await browser.close();

  const result = {
    ok: pageErrors.length === 0,
    htmlPath,
    pngPath,
    annotationsPath,
    width: annotations.canvas.width,
    height: annotations.canvas.height,
    pageErrors,
    generatedAt: new Date().toISOString()
  };

  fs.writeFileSync(verifyPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result, null, 2));

  if (!result.ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
