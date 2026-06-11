const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const appPath = path.join(root, "frontend", "assets", "app.js");
const serverPath = path.join(root, "backend", "server.py");

function requireCondition(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const app = fs.readFileSync(appPath, "utf8");
const server = fs.readFileSync(serverPath, "utf8");

requireCondition(server.includes('"ridershipForecast": RIDERSHIP_FORECAST'), "bootstrap must expose ridershipForecast");
requireCondition(app.includes("function findRidershipForecast("), "frontend must provide a forecast lookup helper");
requireCondition(app.includes("function rollupRidershipForecast("), "frontend must roll up station forecast records");
requireCondition(app.includes("ridershipForecast ? { key: \"ridershipForecast\""), "local station context must label forecast source");
requireCondition(app.includes("function formatForecastRidership("), "station context UI must format forecast ridership separately");
requireCondition(app.includes("现状客流"), "station context UI must label observed ridership separately");
requireCondition(app.includes("预测客流"), "station context UI must label forecast ridership separately");
requireCondition(app.includes("0528既有线路客流预测数据.xls"), "frontend forecast card must cite the source workbook fallback");

console.log(JSON.stringify({
  ok: true,
  checked: [
    "bootstrap ridershipForecast",
    "frontend lookup",
    "frontend rollup",
    "separate observed/forecast station context display",
  ],
}, null, 2));
