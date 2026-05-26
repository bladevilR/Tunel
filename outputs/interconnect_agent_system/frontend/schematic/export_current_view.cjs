const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const root = __dirname;
const outputDir = path.join(root, "exports");
const timestamp = new Date().toISOString().replace(/[:.]/g, "").slice(0, 15);
const outputPath = path.join(outputDir, `amap-3d-export-${timestamp}.png`);
const url = process.env.AMAP_EXPORT_URL || "http://127.0.0.1:8765/schematic/index.html?view=3d&export=1";
const viewport = { width: 1600, height: 960, deviceScaleFactor: 1 };

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function resolveBrowserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    process.env.CHROME_EXECUTABLE,
    process.env.EDGE_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function runtimeCheck() {
  const browserExecutable = resolveBrowserExecutable() || null;
  return {
    ok: Boolean(browserExecutable) && typeof WebSocket === "function",
    automation: "chrome-devtools-protocol",
    externalAutomationDependency: false,
    node: process.version,
    browserExecutable,
    webSocketAvailable: typeof WebSocket === "function"
  };
}

function classifyPageErrors(pageErrors) {
  const pageWarnings = [];
  const fatalPageErrors = [];
  for (const message of pageErrors) {
    if (/Invalid Object: Pixel\(NaN, [^)]+\)/.test(String(message))) {
      pageWarnings.push(message);
    } else {
      fatalPageErrors.push(message);
    }
  }
  return { fatalPageErrors, pageWarnings };
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

function requestJson(port, method, requestPath, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const request = http.request(
      {
        host: "127.0.0.1",
        port,
        path: requestPath,
        method,
        timeout: timeoutMs
      },
      (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          if ((response.statusCode || 500) >= 400) {
            reject(new Error(`${method} ${requestPath} returned ${response.statusCode}: ${body.slice(0, 500)}`));
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(new Error(`Invalid DevTools JSON from ${requestPath}: ${error.message}`));
          }
        });
      }
    );
    request.on("timeout", () => request.destroy(new Error(`${method} ${requestPath} timed out`)));
    request.on("error", reject);
    request.end();
  });
}

async function waitForDevTools(port, browserProcess, stderrChunks) {
  const deadline = Date.now() + 15000;
  let lastError = "";
  while (Date.now() < deadline) {
    if (browserProcess.exitCode !== null) {
      throw new Error(`Browser exited early with code ${browserProcess.exitCode}: ${stderrChunks.join("").slice(-2000)}`);
    }
    try {
      return await requestJson(port, "GET", "/json/version", 1000);
    } catch (error) {
      lastError = error.message;
      await delay(250);
    }
  }
  throw new Error(`Timed out waiting for browser DevTools endpoint: ${lastError}`);
}

async function createPageTarget(port) {
  const target = encodeURIComponent("about:blank");
  try {
    return await requestJson(port, "PUT", `/json/new?${target}`);
  } catch (_error) {
    try {
      return await requestJson(port, "GET", `/json/new?${target}`);
    } catch (_fallbackError) {
      const targets = await requestJson(port, "GET", "/json/list");
      const page = Array.isArray(targets) ? targets.find((item) => item.type === "page") : null;
      if (!page) {
        throw new Error("No Chrome DevTools page target is available");
      }
      return page;
    }
  }
}

function connectWebSocket(webSocketUrl) {
  if (typeof WebSocket !== "function") {
    throw new Error("The current Node.js runtime does not provide WebSocket. Use Node.js 20+ or install a newer Node.js.");
  }
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(webSocketUrl);
    const failTimer = setTimeout(() => reject(new Error("Timed out connecting to Chrome DevTools WebSocket")), 10000);
    socket.addEventListener("open", () => {
      clearTimeout(failTimer);
      resolve(socket);
    });
    socket.addEventListener("error", () => {
      clearTimeout(failTimer);
      reject(new Error("Failed to connect to Chrome DevTools WebSocket"));
    });
  });
}

class CdpSession {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.onEvent = null;
    socket.addEventListener("message", (event) => this.handleMessage(event.data));
    socket.addEventListener("close", () => {
      for (const { reject } of this.pending.values()) {
        reject(new Error("Chrome DevTools WebSocket closed"));
      }
      this.pending.clear();
    });
  }

  handleMessage(data) {
    const text = typeof data === "string" ? data : Buffer.from(data).toString("utf8");
    const message = JSON.parse(text);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject, timer } = this.pending.get(message.id);
      clearTimeout(timer);
      this.pending.delete(message.id);
      if (message.error) {
        reject(new Error(`${message.error.message || "CDP command failed"} ${message.error.data || ""}`.trim()));
      } else {
        resolve(message.result || {});
      }
      return;
    }
    if (this.onEvent) {
      this.onEvent(message);
    }
  }

  send(method, params = {}, timeoutMs = 15000) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timed out`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(payload);
    });
  }

  close() {
    if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
      this.socket.close();
    }
  }
}

async function evaluateValue(session, expression, timeoutMs = 5000) {
  const response = await session.send(
    "Runtime.evaluate",
    {
      expression,
      returnByValue: true,
      awaitPromise: true
    },
    timeoutMs
  );
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.text || "Runtime.evaluate failed");
  }
  return response.result ? response.result.value : undefined;
}

async function waitForExpression(session, expression, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = "";
  while (Date.now() < deadline) {
    try {
      if (await evaluateValue(session, expression, 2000)) {
        return;
      }
    } catch (error) {
      lastError = error.message;
    }
    await delay(250);
  }
  throw new Error(`Timed out waiting for page condition: ${expression}${lastError ? ` (${lastError})` : ""}`);
}

async function captureScreenshot(session, pngPath) {
  const metrics = await session.send("Page.getLayoutMetrics");
  const contentSize = metrics.cssContentSize || metrics.contentSize || {};
  const width = Math.ceil(Math.max(viewport.width, contentSize.width || 0));
  const height = Math.ceil(Math.max(viewport.height, contentSize.height || 0));
  const screenshot = await session.send(
    "Page.captureScreenshot",
    {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: true,
      clip: { x: 0, y: 0, width, height, scale: 1 }
    },
    30000
  );
  fs.writeFileSync(pngPath, Buffer.from(screenshot.data, "base64"));
}

function launchBrowser(browserExecutable, port, userDataDir) {
  const args = [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    "--remote-allow-origins=*",
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-gpu",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
    "--use-gl=swiftshader",
    "about:blank"
  ];
  return spawn(browserExecutable, args, {
    stdio: ["ignore", "ignore", "pipe"],
    windowsHide: true
  });
}

async function closeBrowser(session, browserProcess, userDataDir) {
  if (session) {
    try {
      await session.send("Browser.close", {}, 3000);
    } catch (_error) {
      session.close();
    }
  }
  await delay(400);
  if (browserProcess && browserProcess.exitCode === null) {
    browserProcess.kill();
  }
  fs.rmSync(userDataDir, { recursive: true, force: true });
}

async function main() {
  if (process.argv.includes("--check-runtime")) {
    const check = runtimeCheck();
    process.stdout.write(`${JSON.stringify(check, null, 2)}\n`);
    if (!check.ok) {
      process.exitCode = 1;
    }
    return;
  }

  const check = runtimeCheck();
  if (!check.browserExecutable) {
    throw new Error("PNG 导出需要本机安装 Chrome 或 Microsoft Edge，当前没有找到可用浏览器。");
  }
  if (!check.webSocketAvailable) {
    throw new Error("PNG 导出需要 Node.js 20+ 的 WebSocket 支持。请升级 Node.js 后重试。");
  }

  fs.mkdirSync(outputDir, { recursive: true });
  const port = await findFreePort();
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "interconnect-export-"));
  const browserProcess = launchBrowser(check.browserExecutable, port, userDataDir);
  const stderrChunks = [];
  browserProcess.stderr.on("data", (chunk) => stderrChunks.push(String(chunk)));

  let session = null;
  try {
    await waitForDevTools(port, browserProcess, stderrChunks);
    const target = await createPageTarget(port);
    if (!target.webSocketDebuggerUrl) {
      throw new Error("Chrome DevTools target did not expose a WebSocket URL");
    }
    const socket = await connectWebSocket(target.webSocketDebuggerUrl);
    session = new CdpSession(socket);

    const pageErrors = [];
    const failedRequests = [];
    session.onEvent = (event) => {
      if (event.method === "Runtime.exceptionThrown") {
        const details = event.params && event.params.exceptionDetails;
        pageErrors.push(details && details.text ? details.text : "Runtime exception");
      }
      if (event.method === "Network.loadingFailed") {
        failedRequests.push({
          url: event.params ? event.params.requestId : "unknown",
          errorText: event.params ? event.params.errorText : "unknown"
        });
      }
    };

    await session.send("Network.enable");
    await session.send("Runtime.enable");
    await session.send("Page.enable");
    await session.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: viewport.deviceScaleFactor,
      mobile: false
    });
    await session.send("Page.navigate", { url }, 15000);
    await waitForExpression(session, "document.readyState === 'complete'", 45000);
    await waitForExpression(
      session,
      "document.body && (document.body.dataset.ready === 'true' || document.body.dataset.ready === 'failed')",
      45000
    );
    const ready = await evaluateValue(session, "document.body ? document.body.dataset.ready : ''");
    if (ready === "failed") {
      const message = await evaluateValue(
        session,
        "document.querySelector('#status')?.textContent || document.body.innerText.slice(0, 500) || '页面加载失败'"
      );
      throw new Error(`页面未完成导出准备：${message}`);
    }
    await delay(2600);
    await captureScreenshot(session, outputPath);

    const { fatalPageErrors, pageWarnings } = classifyPageErrors(pageErrors);
    const result = {
      ok: fatalPageErrors.length === 0,
      outputPath,
      url,
      automation: "chrome-devtools-protocol",
      pageErrors: fatalPageErrors,
      pageWarnings,
      failedRequests: failedRequests.filter((item) => !String(item.url).includes("favicon.ico")).slice(0, 12)
    };
    fs.writeFileSync(path.join(root, "last_export.json"), `${JSON.stringify(result, null, 2)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    if (!result.ok) {
      process.exitCode = 1;
    }
  } finally {
    await closeBrowser(session, browserProcess, userDataDir);
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exit(1);
});
