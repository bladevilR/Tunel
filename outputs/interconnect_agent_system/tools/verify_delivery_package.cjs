const REQUIRED_FILES = [
  "README.md",
  "run.ps1",
  "backend/server.py",
  "verify_system.cjs",
  "tools/seed_station_projects.py",
  "tools/verify_station_precheck.cjs",
  "tools/verify_report_richness.cjs",
  "tools/verify_delivery_package.cjs",
  "docs/delivery_notes.md",
  "docs/acceptance_report.md",
  "docs/api_reference.md",
  "docs/delivery_manifest.md",
  "docs/function_and_gap_inventory.md",
  "docs/knowledge_database.md",
  "docs/feedback_20260507_analysis.md",
  "docs/llm_integration_contract.md",
  "docs/pilot_input_template.xlsx"
];

const BASE_URL = process.env.INTERCONNECT_BASE_URL || "http://127.0.0.1:8765";

function fail(message, detail = {}) {
  console.error(JSON.stringify({ ok: false, message, detail }, null, 2));
  process.exit(1);
}

async function fetchJson(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    fail(`接口请求失败：${path}`, { status: response.status });
  }
  return response.json();
}

async function main() {
  const manifest = await fetchJson("/api/delivery/manifest");
  if (!manifest.ok) {
    fail("交付清单接口未返回 ok=true", manifest);
  }

  const relativePaths = new Set((manifest.files || []).map((file) => file.relativePath));
  const missing = REQUIRED_FILES.filter((file) => !relativePaths.has(file));
  if (missing.length) {
    fail("交付清单缺少必需文件", { missing, totalFiles: manifest.totalFiles });
  }

  const groups = new Map((manifest.groups || []).map((group) => [group.id, group]));
  for (const id of ["runtime", "docs", "screenshots", "mockups", "exports"]) {
    if (!groups.has(id)) {
      fail("交付清单缺少必要分组", { missingGroup: id });
    }
  }
  if ((groups.get("docs")?.files || []).length < 9) {
    fail("交付文档分组数量不足", { docsCount: groups.get("docs")?.files?.length || 0 });
  }
  if ((groups.get("runtime")?.files || []).length < 8) {
    fail("运行与验收入口分组数量不足", { runtimeCount: groups.get("runtime")?.files?.length || 0 });
  }

  const packageResponse = await fetch(`${BASE_URL}/api/delivery/package`);
  if (!packageResponse.ok) {
    fail("交付包下载失败", { status: packageResponse.status });
  }
  const contentType = packageResponse.headers.get("content-type") || "";
  if (!contentType.includes("application/zip")) {
    fail("交付包响应类型不是 zip", { contentType });
  }
  const buffer = Buffer.from(await packageResponse.arrayBuffer());
  const signature = buffer.subarray(0, 2).toString("hex");
  if (signature !== "504b" || buffer.length < 1024) {
    fail("交付包文件头或大小异常", { signature, size: buffer.length });
  }

  console.log(JSON.stringify({
    ok: true,
    totalFiles: manifest.totalFiles,
    totalSize: manifest.totalSize,
    docsCount: groups.get("docs").files.length,
    runtimeCount: groups.get("runtime").files.length,
    package: {
      contentType,
      size: buffer.length,
      signature
    }
  }, null, 2));
}

main().catch((error) => fail("交付包专项验收异常", { error: error.message }));
