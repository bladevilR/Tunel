const state = {
  bootstrap: null,
  currentProject: null,
  currentResult: null,
  currentProjectId: null,
  projects: [],
  exports: [],
  lastKnowledgeResults: [],
  offlineFallbackConsent: false,
  evaluating: false,
  progressTimer: null,
  stationSearchTimer: null,
  selectedStationContext: null,
  reportMode: "client_formal"
};

const PROJECT_INTAKE_SCHEMA_VERSION = "interconnect.project-intake.v1";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const PAGE_META = {
  dashboard: ["总览工作台", "面向项目研判、方案比选和顾问报告输出的统一工作台。"],
  assessment: ["项目评估", "录入真实项目字段，调用后端评分并输出推荐方案。"],
  knowledge: ["依据检索", "检索站点、客流、出入口与周边配套等支撑资料。"],
  reporting: ["报告输出", "预览顾问式报告，生成可提交的成果文件。"]
};

const CATEGORY_LABELS = {
  work_plan: "评估框架",
  feedback: "项目反馈",
  scoring: "评分依据",
  input_schema: "录入标准",
  ridership: "客流数据",
  station_tod: "TOD站点",
  station_interface: "出入口接口",
  station_amenities: "周边配套",
  design_guidance: "设计导则",
  early_reference: "早期参考",
  visual_reference: "视觉参考",
  office_temp: "临时文件"
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    let detail = "";
    try {
      const payload = await response.json();
      detail = typeof payload.error === "string" ? payload.error : (payload.error?.message || JSON.stringify(payload.error || payload));
    } catch (error) {
      detail = await response.text().catch(() => "");
    }
    throw new Error(detail || `API ${path} failed: ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : "0";
}

function clipText(value, maxLength = 260) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function safeDownloadSlug(value, fallback = "project-intake") {
  const slug = String(value || fallback)
    .trim()
    .replace(/[^\w\u4e00-\u9fff-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || fallback;
}

function lineCount(value) {
  return String(value || "").split(/[\/、,，\s]+/).filter(Boolean).length;
}

function inferStationTypeFromLine(line, stationName = "") {
  if (lineCount(line) >= 2) return "current_transfer";
  return stationName ? "normal" : "";
}

function stationTypeLabel(value) {
  const labels = {
    current_transfer: "现状换乘站",
    planned_transfer: "规划换乘站",
    normal: "一般站"
  };
  return labels[value] || value || "待补齐";
}

function readableKind(kind) {
  const labels = {
    xlsx_rows: "表格行",
    xlsx_sheet: "工作表",
    docx_paragraph: "文档段落",
    pptx_slide: "材料页",
    pdf_page: "PDF页",
    json_record: "结构化记录",
    rule_card: "评估依据",
    station_record: "站点记录"
  };
  return labels[kind] || kind || "资料片段";
}

function rawMax(result) {
  return Number(result?.scoreScale?.rawMax || state.bootstrap?.factors?.scoreScale?.rawMax || 0);
}

function getNested(target, path) {
  return path.split(".").reduce((cursor, key) => (cursor ? cursor[key] : undefined), target);
}

function setNested(target, path, value) {
  const parts = path.split(".");
  let cursor = target;
  while (parts.length > 1) {
    const key = parts.shift();
    cursor[key] = cursor[key] || {};
    cursor = cursor[key];
  }
  cursor[parts[0]] = value;
}

function stationAliases(name) {
  const text = (name || "").trim();
  if (!text) return [];
  const aliases = [text];
  for (const match of text.matchAll(/[（(]([^）)]+)[）)]/g)) aliases.push(match[1].trim());
  const noParen = text.replace(/[（(].*?[）)]/g, "").trim();
  if (noParen) aliases.push(noParen);
  if (noParen.endsWith("站")) aliases.push(noParen.slice(0, -1));
  return Array.from(new Set(aliases.filter(Boolean)));
}

function aliasMatches(inputName, candidateNames) {
  const inputAliases = new Set(stationAliases(inputName));
  for (const name of candidateNames || []) {
    for (const alias of stationAliases(name)) {
      if (inputAliases.has(alias)) return true;
    }
  }
  return false;
}

function findFactor(factorId) {
  for (const dimension of state.bootstrap.factors.dimensions) {
    const factor = dimension.factors.find((item) => item.id === factorId);
    if (factor) return factor;
  }
  return null;
}

function findRidership(stationName) {
  return (state.bootstrap.ridership?.records || []).find((item) => aliasMatches(stationName, [item.stationName]));
}

function findStationMemory(stationName) {
  return (state.bootstrap.stationMemory?.records || []).find((item) => {
    const identity = item.identity || {};
    return aliasMatches(stationName, [identity.canonicalName, identity.displayName, ...(identity.aliases || [])]);
  });
}

function splitLineTokens(value) {
  return String(value || "")
    .split(/[/,;|、，\s]+/)
    .map((item) => item.trim().replace(/^0+/, ""))
    .filter(Boolean);
}

function ridershipForecastRecords(stationName, line = "") {
  const records = (state.bootstrap.ridershipForecast?.records || []).filter((item) => {
    return aliasMatches(stationName, [item.stationName, item.stationDisplayName]);
  });
  const requestedLines = new Set(splitLineTokens(line));
  if (!requestedLines.size) return records;
  const filtered = records.filter((item) => requestedLines.has(String(item.line || "").replace(/^0+/, "")));
  return filtered.length ? filtered : records;
}

function rollupRidershipForecast(records) {
  if (!records.length) return null;
  const payload = state.bootstrap.ridershipForecast || {};
  const source = payload.source?.fileName || payload.source || "0528既有线路客流预测数据.xls";
  const horizons = new Map();
  for (const record of records) {
    const key = String(record.horizonYear || record.year || "");
    if (!key) continue;
    if (!horizons.has(key)) {
      horizons.set(key, {
        horizonYear: Number.isFinite(Number(key)) ? Number(key) : key,
        boardingTotal: 0,
        alightingTotal: 0,
        directions: []
      });
    }
    const bucket = horizons.get(key);
    const boarding = Number(record.boarding || 0);
    const alighting = Number(record.alighting || 0);
    bucket.boardingTotal += Number.isFinite(boarding) ? boarding : 0;
    bucket.alightingTotal += Number.isFinite(alighting) ? alighting : 0;
    bucket.directions.push({
      line: record.line,
      directionLabel: record.directionLabel || "",
      boarding,
      alighting
    });
  }
  return {
    source,
    unit: payload.unit || "人次",
    count: records.length,
    lines: Array.from(new Set(records.map((item) => String(item.line || "").replace(/^0+/, "")).filter(Boolean))).sort(),
    horizons: Array.from(horizons.values()).sort((a, b) => String(a.horizonYear).localeCompare(String(b.horizonYear), "zh-CN")),
    records
  };
}

function findRidershipForecast(stationName, line = "") {
  return rollupRidershipForecast(ridershipForecastRecords(stationName, line));
}

function findStationOperations(stationName) {
  return (state.bootstrap.stationOperations?.records || []).find((item) => {
    return aliasMatches(stationName, [item.name, ...(item.aliases || []), ...(item.displayNames || [])]);
  });
}

function findStationAmenities(stationName) {
  return (state.bootstrap.stationAmenities?.records || []).find((item) => {
    return aliasMatches(stationName, [item.name, ...(item.aliases || []), ...(item.displayNames || [])]);
  });
}

function sourceManifest() {
  return Array.isArray(state.bootstrap?.sourceManifest) ? state.bootstrap.sourceManifest : [];
}

function unparsedSources() {
  return Array.isArray(state.bootstrap?.unparsedSources) ? state.bootstrap.unparsedSources : [];
}

function categoryName(category) {
  return CATEGORY_LABELS[category] || category || "资料";
}

function statusLabel(status) {
  const labels = {
    parsed: "已解析",
    metadata_only: "元数据",
    unparsed: "待处理",
    ignored: "已忽略"
  };
  return labels[status] || status || "未知";
}

function statusClass(status) {
  if (status === "parsed") return "ok";
  if (status === "metadata_only") return "warn";
  if (status === "ignored") return "muted";
  return "bad";
}

function populateFactorSelect(select) {
  const factor = findFactor(select.dataset.factor);
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "待补齐";
  select.appendChild(empty);
  for (const option of factor.options) {
    const node = document.createElement("option");
    node.value = option.value;
    node.textContent = `${option.label}（${option.score}分）`;
    select.appendChild(node);
  }
}

function populateBootstrap() {
  for (const select of $$("select[data-factor]")) populateFactorSelect(select);

  const stationList = $("#stationList");
  stationList.innerHTML = "";
  for (const station of state.bootstrap.stations.stations) {
    const option = document.createElement("option");
    option.value = station.name;
    option.label = `${station.todLevel} / ${station.lines || "线路待补齐"}`;
    stationList.appendChild(option);
  }

  const demoSelect = $("#demoSelect");
  demoSelect.innerHTML = "";
  for (const item of state.bootstrap.demos.cases) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    demoSelect.appendChild(option);
  }

  const categoryFilter = $("#knowledgeCategoryFilter");
  categoryFilter.innerHTML = `<option value="">全部范围</option>`;
  const categories = Array.from(new Set(sourceManifest().map((item) => item.category).filter(Boolean)));
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = categoryName(category);
    categoryFilter.appendChild(option);
  }

  state.projects = state.bootstrap.projects || [];
  state.exports = state.bootstrap.exports || [];
  renderDashboard();
  renderProjectLibrary();
  renderKnowledgeSummary();
  renderSourceManifest();
  renderExportHistory();
  renderRuleSummary();
}

function normalizeFieldValue(input) {
  if (input.type === "number") {
    if (input.value === "") return null;
    return Number(input.value);
  }
  return input.value.trim();
}

function collectProject() {
  const project = structuredClone(state.currentProject || {});
  for (const field of $$("#projectForm [name]")) {
    setNested(project, field.name, normalizeFieldValue(field));
  }
  return project;
}

function fillProject(project) {
  const savedIds = new Set((state.projects || []).map((item) => item.id));
  state.currentProjectId = savedIds.has(project.id) ? project.id : null;
  state.currentProject = structuredClone(project);
  for (const field of $$("#projectForm [name]")) {
    const value = getNested(project, field.name);
    field.value = value ?? "";
    delete field.dataset.stationAutofilled;
    delete field.dataset.stationUserOwned;
    delete field.dataset.stationAutofillSource;
  }
  $("#projectSelect").value = state.currentProjectId || "";
  updateActionStates();
}

function selectedDemo() {
  return state.bootstrap.demos.cases.find((item) => item.id === $("#demoSelect").value);
}

function setAutofilledStationField(selector, value, sourceLabel = "station context") {
  const field = $(selector);
  if (!field) return;
  const next = value ?? "";
  if (next === "") return;
  if (field.dataset.stationUserOwned === "true") return;
  field.value = next;
  field.dataset.stationAutofilled = "true";
  field.dataset.stationAutofillSource = sourceLabel;
  delete field.dataset.stationUserOwned;
}

function bindStationAutofillOwnership() {
  const selectors = [
    '[name="station.todLevel"]',
    '[name="station.locationLevel"]',
    '[name="station.line"]',
    '[name="station.dailyInbound"]',
    '[name="station.district"]',
    '[name="station.nearbyExit"]',
    '[name="station.interfaceCondition"]',
    '[name="station.stationType"]'
  ];
  for (const selector of selectors) {
    const field = $(selector);
    if (!field) continue;
    ["input", "change"].forEach((eventName) => {
      field.addEventListener(eventName, () => {
        if (field.value.trim()) {
          field.dataset.stationUserOwned = "true";
          delete field.dataset.stationAutofilled;
          delete field.dataset.stationAutofillSource;
        } else {
          delete field.dataset.stationUserOwned;
        }
      });
    });
  }
}

function localStationContext(stationName) {
  const station = state.bootstrap.stations.stations.find((item) => aliasMatches(stationName, [item.name]));
  const memory = findStationMemory(stationName);
  const memoryContext = memory?.context || {};
  const ridership = findRidership(stationName);
  const operations = findStationOperations(stationName);
  const amenities = findStationAmenities(stationName);
  const line = memoryContext.line || station?.lines || ridership?.lines || (operations?.lines || amenities?.lines || []).join("/");
  const ridershipForecast = findRidershipForecast(stationName, line);
  const fields = {
    "station.name": memory?.identity?.canonicalName || station?.name || stationName,
    "station.todLevel": memoryContext.todLevel || station?.todLevel || "",
    "station.locationLevel": memoryContext.locationLevel || station?.locationLevel || "",
    "station.line": line || "",
    "station.stationType": memoryContext.stationType || inferStationTypeFromLine(line, station?.name || stationName),
    "station.dailyInbound": memoryContext.dailyInbound || (ridership?.latestDailyInbound ? Math.round(ridership.latestDailyInbound) : ""),
    "station.district": memoryContext.district || operations?.districts?.[0] || "",
    "station.nearbyExit": memoryContext.nearbyExit || amenities?.sampleExits?.[0]?.exit || "",
    "station.interfaceCondition": memoryContext.interfaceCondition || ""
  };
  if (operations) {
    const forms = operations.connectionForms?.length ? operations.connectionForms.join("、") : "暂无已登记联通形式";
    fields["station.interfaceCondition"] = `已识别出入口${operations.exitCount || 0}个；联通形式：${forms}；问题记录${operations.issueCount || 0}条。`;
  }
  return {
    ok: Boolean(memory || station || ridership || ridershipForecast || operations || amenities),
    query: stationName,
    name: fields["station.name"],
    suggestedFields: fields,
    memory,
    ridershipForecast,
    sources: [
      memory ? { key: "memory", label: "station memory", matched: true } : null,
      station ? { key: "station", label: "TOD station preset", matched: true } : null,
      ridership ? { key: "ridership", label: "ridership workbook", matched: true } : null,
      ridershipForecast ? { key: "ridershipForecast", label: "ridership forecast workbook", matched: true } : null,
      operations ? { key: "operations", label: "station interface workbook", matched: true } : null,
      amenities ? { key: "amenities", label: "station amenity workbook", matched: true } : null
    ].filter(Boolean)
  };
}

function applyStationContext(context, options = {}) {
  if (!context?.suggestedFields) return;
  state.selectedStationContext = context;
  const sourceLabel = (context.sources || []).map((item) => item.label).join(", ") || "station context";
  for (const [path, value] of Object.entries(context.suggestedFields)) {
    if (path === "station.name") continue;
    setAutofilledStationField(`[name="${path}"]`, value, sourceLabel);
  }
  if (options.explicit) {
    const panel = $("#stationSearchResults");
    if (panel) panel.hidden = true;
  }
}

function setStationMemoryStatus(message, mode = "info") {
  const node = $("#stationMemoryStatus");
  if (!node) return;
  node.textContent = message || "";
  node.dataset.mode = mode;
}

function stationMemoryPayloadFromProject(project) {
  const station = project.station || {};
  return {
    stationName: station.name || "",
    project,
    identity: {
      canonicalName: station.name || "",
      displayName: station.name ? `${station.name}站` : "",
      aliases: station.name ? stationAliases(station.name) : []
    },
    context: {
      line: station.line || "",
      todLevel: station.todLevel || "",
      locationLevel: station.locationLevel || "",
      stationType: station.stationType || "",
      district: station.district || "",
      dailyInbound: station.dailyInbound ?? null,
      nearbyExit: station.nearbyExit || "",
      interfaceCondition: station.interfaceCondition || ""
    },
    sourceLabels: (state.selectedStationContext?.sources || []).map((item) => item.label),
    operatorIntent: "save_station_memory"
  };
}

async function saveStationMemory() {
  const project = collectProject();
  if (!project.station?.name) {
    setStationMemoryStatus("先选择站点", "error");
    return;
  }
  const button = $("#saveStationMemoryBtn");
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "保存中";
  try {
    const response = await api("/api/station-memory", {
      method: "POST",
      body: JSON.stringify(stationMemoryPayloadFromProject(project))
    });
    state.bootstrap.stationMemory = {
      ...(state.bootstrap.stationMemory || {}),
      records: response.records || [response.record]
    };
    state.selectedStationContext = {
      ...(state.selectedStationContext || {}),
      memory: response.record
    };
    setStationMemoryStatus(`已保存：${response.record.identity?.canonicalName || project.station.name}`, "ok");
  } catch (error) {
    setStationMemoryStatus(`保存失败：${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function applyStationMemory() {
  const project = collectProject();
  const stationName = project.station?.name || state.selectedStationContext?.name || "";
  if (!stationName) {
    setStationMemoryStatus("先选择站点", "error");
    return;
  }
  const button = $("#applyStationMemoryBtn");
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "应用中";
  try {
    const response = await api("/api/station-memory/apply", {
      method: "POST",
      body: JSON.stringify({
        stationName,
        memoryId: state.selectedStationContext?.memory?.id,
        project,
        force: true
      })
    });
    fillProject(response.project);
    state.selectedStationContext = await fetchStationContext(response.project.station?.name || stationName);
    setStationMemoryStatus(`已应用版本 ${response.snapshot?.sourceVersion || ""}`, "ok");
  } catch (error) {
    setStationMemoryStatus(`应用失败：${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function fetchStationContext(stationName) {
  return api(`/api/stations/context?name=${encodeURIComponent(stationName)}`);
}

async function autofillStationByName() {
  const stationName = $('[name="station.name"]').value.trim();
  if (!stationName) return;
  try {
    const context = await fetchStationContext(stationName);
    if (context.ok) {
      applyStationContext(context);
      return;
    }
  } catch (error) {
    console.warn("station context API unavailable, using bootstrap data", error);
  }
  const fallback = localStationContext(stationName);
  if (fallback.ok) applyStationContext(fallback);
}

function researchOptions() {
  const localOverride = window.localStorage?.getItem("modelLedUiOfflineFallback") === "1";
  if (localOverride) return { allowOfflineFallback: true, forceOfflineFallback: true };
  return state.offlineFallbackConsent ? { allowOfflineFallback: true } : {};
}

async function requestEvaluation(project) {
  const options = researchOptions();
  const body = Object.keys(options).length ? { project, researchOptions: options } : project;
  const response = await api("/api/evaluate", {
    method: "POST",
    body: JSON.stringify(body)
  });
  return response.result;
}

function setEvaluationProgress(active, projectName = "") {
  const panel = $("#evaluationProgress");
  const title = $("#evaluationProgressTitle");
  const text = $("#evaluationProgressText");
  const bar = $("#evaluationProgressBar");
  const button = $("#evaluateBtn");
  const exportButton = $("#exportBtn");
  const steps = [
    ["正在读取项目条件", 12],
    ["正在检索本地案例与支撑资料", 28],
    ["正在调用模型进行综合研判", 48],
    ["正在撰写长篇顾问报告", 72],
    ["正在整理结论、依据和实施建议", 88]
  ];
  if (!active) {
    state.evaluating = false;
    if (state.progressTimer) {
      clearInterval(state.progressTimer);
      state.progressTimer = null;
    }
    if (panel) panel.hidden = true;
    if (button) {
      button.disabled = false;
      button.textContent = "运行评估";
    }
    if (exportButton) exportButton.disabled = false;
    if (bar) bar.style.width = "100%";
    return;
  }
  state.evaluating = true;
  if (panel) panel.hidden = false;
  if (title) title.textContent = projectName ? `正在生成：${projectName}` : "正在生成顾问报告";
  if (button) {
    button.disabled = true;
    button.textContent = "模型生成中";
  }
  if (exportButton) exportButton.disabled = true;
  let index = 0;
  const renderStep = () => {
    const [label, width] = steps[Math.min(index, steps.length - 1)];
    if (text) text.textContent = `${label}，请稍候。`;
    if (bar) bar.style.width = `${width}%`;
    index += 1;
  };
  renderStep();
  if (state.progressTimer) clearInterval(state.progressTimer);
  state.progressTimer = setInterval(renderStep, 7000);
}

function renderReportLoading(projectName) {
  const node = $("#reportPreview");
  if (!node) return;
  node.className = "report-preview";
  node.innerHTML = `
    <section class="report-loading">
      <div class="report-loading-pulse" aria-hidden="true"></div>
      <div>
        <h2>正在生成综合顾问报告</h2>
        <p>${escapeHtml(projectName || "当前项目")} 的报告正在由模型撰写，完成后会直接显示完整正文。</p>
      </div>
    </section>
  `;
}

function clearEvaluationOutput(message = "请选择项目并点击“运行评估”，系统将调用模型生成完整顾问报告。") {
  state.currentResult = null;
  $("#completenessValue").textContent = "--";
  $("#scoreValue").textContent = "--";
  $("#levelValue").textContent = "--";
  $("#typeValue").textContent = "--";
  $("#provisionalBadge").textContent = "待运行";
  $("#provisionalBadge").className = "pill muted";
  $("#resultSummary").innerHTML = `<p>${escapeHtml(message)}</p>`;
  $("#stationContextPanel").innerHTML = "";
  $("#missingList").innerHTML = "";
  $("#recommendationBody").textContent = message;
  $("#scoreMatrix").innerHTML = "";
  $("#ruleSummary").innerHTML = "";
  $("#reportPreview").className = "report-preview empty-state";
  $("#reportPreview").innerHTML = `
    <section class="report-empty-action">
      <div>
        <h2>尚未生成报告</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    </section>
  `;
  renderDashboard();
}

async function runEvaluation() {
  await autofillStationByName();
  const project = collectProject();
  if (state.currentProjectId) project.id = state.currentProjectId;
  state.currentProject = project;
  setEvaluationProgress(true, project.name || project.station?.name || "");
  renderReportLoading(project.name || project.station?.name || "");
  try {
    const result = await requestEvaluation(project);
    state.currentResult = result;
    renderResult(result);
    renderDashboard();
    return result;
  } finally {
    setEvaluationProgress(false);
  }
}

function renderProjectLibrary() {
  const select = $("#projectSelect");
  select.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = state.projects.length ? `选择站点/项目（${state.projects.length}个）` : "暂无站点项目";
  select.appendChild(empty);
  for (const project of state.projects) {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = `${project.name} / ${project.level || "未评估"}`;
    select.appendChild(option);
  }
  $("#projectCountValue").textContent = `${state.projects.length} 个项目`;
  renderProjectTable();
  updateActionStates();
}

function renderProjectTable() {
  const body = $("#projectTableBody");
  if (!state.projects.length) {
    body.innerHTML = `<tr><td colspan="5" class="empty-cell">暂无保存项目，可先载入示例或录入真实地块后保存。</td></tr>`;
    return;
  }
  body.innerHTML = state.projects.map((project) => `
    <tr>
      <td><button class="text-btn" data-project-id="${escapeHtml(project.id)}">${escapeHtml(project.name)}</button><small>${escapeHtml(project.projectCode || "")}</small></td>
      <td>${escapeHtml(project.stationName || "待补齐")}</td>
      <td><span class="status-badge ok">${escapeHtml(project.level || "未评估")}</span></td>
      <td>${escapeHtml(project.recommendedType || "待推荐")}</td>
      <td>${escapeHtml(project.updatedAt || "")}</td>
    </tr>
  `).join("");
  for (const button of $$("#projectTableBody [data-project-id]")) {
    button.addEventListener("click", async () => {
      $("#projectSelect").value = button.dataset.projectId;
      await loadSavedProject();
      showView("assessment");
    });
  }
}

async function refreshProjects(projects) {
  if (projects) {
    state.projects = projects;
  } else {
    const response = await api("/api/projects");
    state.projects = response.projects || [];
  }
  renderProjectLibrary();
}

async function refreshExports() {
  const response = await api("/api/exports");
  state.exports = response.exports || [];
  renderExportHistory();
}

async function saveProject() {
  const button = $("#saveProjectBtn");
  const originalText = button.textContent;
  const project = collectProject();
  if (state.currentProjectId) project.id = state.currentProjectId;
  const options = { ...researchOptions(), skipEvaluation: true };
  const body = Object.keys(options).length ? { project, researchOptions: options } : project;
  button.disabled = true;
  button.textContent = "保存中";
  try {
    const response = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify(body)
    });
    state.currentProjectId = response.record.id;
    state.currentProject = response.record.project;
    clearEvaluationOutput("项目已保存。请点击“运行评估”，系统会重新调用模型生成报告。");
    await refreshProjects(response.projects);
    $("#projectSelect").value = response.record.id;
    $("#lastSavedValue")?.remove();
    updateActionStates();
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function loadSavedProject() {
  const id = $("#projectSelect").value;
  if (!id) return;
  const response = await api(`/api/projects/${encodeURIComponent(id)}`);
  state.currentProjectId = response.record.id;
  fillProject({ ...response.record.project, id: response.record.id });
  clearEvaluationOutput("项目已载入。请点击“运行评估”，系统会重新调用模型生成本次报告。");
}

async function deleteCurrentProject() {
  const id = $("#projectSelect").value;
  if (!id) return;
  const project = state.projects.find((item) => item.id === id);
  const name = project?.name || "当前项目";
  if (!window.confirm(`确认删除“${name}”？删除后将从本地项目库移除，当前表单内容不会作为已保存项目保留。`)) return;
  const response = await api(`/api/projects/${encodeURIComponent(id)}`, { method: "DELETE" });
  state.currentProjectId = null;
  await refreshProjects(response.projects);
  $("#projectSelect").value = "";
  $("#exportPathValue").textContent = "项目已删除，可继续编辑当前表单并另存。";
  $("#exportFiles").innerHTML = "";
  updateActionStates();
}

function setProjectIntakeStatus(message, mode = "info") {
  const node = $("#projectIntakeStatus");
  if (!node) return;
  node.textContent = message || "";
  node.dataset.mode = mode;
}

function projectIntakePayload() {
  const project = collectProject();
  if (state.currentProjectId) project.id = state.currentProjectId;
  return {
    schemaVersion: PROJECT_INTAKE_SCHEMA_VERSION,
    exportedAt: new Date().toISOString(),
    record: {
      id: state.currentProjectId || project.id || null,
      project,
      researchOptions: researchOptions()
    },
    project
  };
}

function validateProjectIntakePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("导入文件不是有效的 JSON 对象");
  }
  const project = payload.project || payload.record?.project;
  if (!project || typeof project !== "object" || Array.isArray(project)) {
    throw new Error("导入文件缺少 project 或 record.project");
  }
  const station = project.station || {};
  if (station && typeof station !== "object") {
    throw new Error("导入文件中的 station 字段格式不兼容");
  }
  return {
    schemaVersion: payload.schemaVersion || "legacy",
    id: payload.record?.id || project.id || null,
    project,
    researchOptions: payload.record?.researchOptions || payload.researchOptions || {}
  };
}

function exportProjectIntake() {
  const payload = projectIntakePayload();
  const project = payload.record.project;
  const slug = safeDownloadSlug(project.projectCode || project.name || project.station?.name);
  downloadJson(`${slug}-project-intake.json`, payload);
  setProjectIntakeStatus("提资 JSON 已生成", "ok");
}

async function importProjectIntakeFile(file) {
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    const intake = validateProjectIntakePayload(payload);
    const project = structuredClone(intake.project);
    if (intake.id) project.id = intake.id;
    fillProject(project);
    clearEvaluationOutput("提资文件已导入。请复核字段后运行评估。");
    await autofillStationByName();
    setProjectIntakeStatus(`已导入：${project.name || project.station?.name || "未命名项目"}`, "ok");
    showView("assessment");
  } catch (error) {
    setProjectIntakeStatus(`导入失败：${error.message}`, "error");
  } finally {
    const input = $("#importProjectIntakeFile");
    if (input) input.value = "";
  }
}

function renderStationSuggestions(results) {
  const panel = $("#stationSearchResults");
  if (!panel) return;
  if (!results.length) {
    panel.hidden = true;
    panel.innerHTML = "";
    return;
  }
  panel.hidden = false;
  panel.innerHTML = results.map((item) => `
    <button type="button" class="station-suggestion" data-station-name="${escapeHtml(item.name)}">
      <strong>${escapeHtml(item.name)}</strong>
      <span>${escapeHtml([item.line, stationTypeLabel(item.stationType), item.todLevel].filter(Boolean).join(" / "))}</span>
      <small>${escapeHtml((item.sourceLabels || []).join(" · "))}</small>
    </button>
  `).join("");
  for (const button of $$("#stationSearchResults [data-station-name]")) {
    button.addEventListener("click", async () => {
      await selectStationSuggestion(button.dataset.stationName);
    });
  }
}

async function searchStationSuggestions() {
  const query = $('[name="station.name"]').value.trim();
  if (!query) {
    renderStationSuggestions([]);
    return;
  }
  try {
    const response = await api(`/api/stations/search?q=${encodeURIComponent(query)}&limit=8`);
    renderStationSuggestions(response.results || []);
  } catch (error) {
    console.warn("station search API unavailable", error);
    const fallback = localStationContext(query);
    renderStationSuggestions(fallback.ok ? [{
      name: fallback.name,
      line: fallback.suggestedFields["station.line"],
      stationType: fallback.suggestedFields["station.stationType"],
      todLevel: fallback.suggestedFields["station.todLevel"],
      sourceLabels: fallback.sources.map((item) => item.label)
    }] : []);
  }
}

function queueStationSearch() {
  window.clearTimeout(state.stationSearchTimer);
  state.stationSearchTimer = window.setTimeout(searchStationSuggestions, 160);
}

async function selectStationSuggestion(stationName) {
  const field = $('[name="station.name"]');
  field.value = stationName;
  try {
    const context = await fetchStationContext(stationName);
    applyStationContext(context, { explicit: true });
  } catch (error) {
    applyStationContext(localStationContext(stationName), { explicit: true });
  }
}

function renderResult(result) {
  $("#completenessValue").textContent = `${result.dataCompleteness.done}/${result.dataCompleteness.total}`;
  $("#scoreValue").textContent = `${result.scorePercent.toFixed(1)} / 100分`;
  $("#levelValue").textContent = result.level;
  $("#typeValue").textContent = result.recommendation.primary.name;
  $("#provisionalBadge").textContent = result.provisional ? "含待补齐" : "核心字段完整";
  $("#provisionalBadge").className = result.provisional ? "pill warn" : "pill";

  renderResultSummary(result);
  renderStationContext(result);
  renderMissing(result);
  renderRecommendation(result);
  renderScoreMatrix(result);
  renderReport(result);
  renderTrace(result);
  renderDashboard();
}

function renderResultSummary(result) {
  const primary = result.recommendation.primary;
  const max = rawMax(result);
  $("#resultSummary").innerHTML = `
    <div><span>百分制得分</span><strong>${result.scorePercent.toFixed(1)} / 100分</strong></div>
    <div><span>原始加权分</span><strong>${result.score.toFixed(4)}${max ? ` / ${max.toFixed(4)}` : ""}</strong></div>
    <div><span>等级</span><strong>${escapeHtml(result.level)}</strong></div>
    <div><span>推荐</span><strong>${escapeHtml(primary.name)}</strong></div>
    <p>${escapeHtml(result.policy)}</p>
  `;
}

function compactNearby(amenities) {
  const nearby = amenities?.nearby || {};
  const values = [
    ...(nearby.schools || []),
    ...(nearby.hubs || []),
    ...(nearby.residential || []),
    ...(nearby.commercial || []),
    ...(nearby.other || [])
  ].filter(Boolean);
  return values.slice(0, 5).join("、") || "待补齐";
}

function formatForecastRidership(forecast) {
  const horizons = forecast?.horizons || [];
  if (!horizons.length) {
    return {
      value: "待补齐",
      source: "未匹配预测客流"
    };
  }
  const summary = horizons.slice(0, 2).map((item) => {
    const year = item.horizonYear || "远期";
    const boarding = formatNumber(Math.round(Number(item.boardingTotal || 0)));
    const alighting = formatNumber(Math.round(Number(item.alightingTotal || 0)));
    return `${year}年 上${boarding}/下${alighting}`;
  }).join("；");
  const lines = (forecast.lines || []).length ? `${forecast.lines.join("/")}号线 · ` : "";
  return {
    value: summary,
    source: `${lines}${forecast.source || "0528既有线路客流预测数据.xls"} · 全日预测${forecast.unit ? `（${forecast.unit}）` : ""}`
  };
}

function renderStationContext(result) {
  const context = result.stationContext || {};
  const operations = context.operations || {};
  const amenities = context.amenities || {};
  const memory = context.memory || {};
  const forecast = formatForecastRidership(context.ridershipForecast);
  $("#stationContextPanel").innerHTML = `
    <div><span>现状客流</span><strong>${context.dailyInbound ? `${Math.round(context.dailyInbound)} 人次/日` : "待补齐"}</strong><small>${escapeHtml(context.dailyInboundSource || "")}</small></div>
    <div class="wide"><span>预测客流</span><strong>${escapeHtml(forecast.value)}</strong><small>${escapeHtml(forecast.source)}</small></div>
    <div class="wide"><span>站点记忆</span><strong>${memory.id ? `版本 ${escapeHtml(memory.version || 1)}` : "暂无记录"}</strong><small>${escapeHtml((memory.provenance?.sourceLabels || []).join("、") || "可保存当前修正")}</small></div>
    <div><span>出入口</span><strong>${operations.exitCount ?? amenities.exitRows ?? "--"} 个</strong><small>接口 ${operations.interfaceCount ?? "--"} 个</small></div>
    <div><span>开放状态</span><strong>${amenities.openExitCount ?? "--"}/${amenities.exitRows ?? "--"}</strong><small>运营管理 ${amenities.managedExitCount ?? "--"} 个</small></div>
    <div><span>联通形式</span><strong>${escapeHtml((operations.connectionForms || []).join("、") || "待补齐")}</strong><small>${escapeHtml((operations.priorityLabels || []).join("、"))}</small></div>
    <div class="wide"><span>周边配套</span><strong>${escapeHtml(compactNearby(amenities))}</strong></div>
  `;
}

function renderRecommendation(result) {
  const primary = result.recommendation.primary;
  const rule = result.recommendation.rule;
  const alternatives = result.recommendation.alternatives;
  $("#recommendationBody").className = "recommendation-body";
  $("#recommendationBody").innerHTML = `
    <div class="rec-title">
      <strong>${escapeHtml(primary.name)}</strong>
      <span>${escapeHtml(primary.category)} / ${escapeHtml(result.level)}</span>
    </div>
    <p class="rec-reason">${escapeHtml(rule.reason)}</p>
    <ul class="param-list">${primary.parameters.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <h3 class="small-heading">备选方案</h3>
    <ul class="alt-list">${alternatives.map((item) => `<li><strong>${escapeHtml(item.name)}</strong>：${escapeHtml(item.bestFor.join("、"))}</li>`).join("")}</ul>
  `;
}

function renderScoreMatrix(result) {
  const node = $("#scoreMatrix");
  node.className = "score-matrix";
  node.innerHTML = result.dimensions.map((dimension) => `
    <div class="dimension-row">
      <div class="dimension-head">
        <strong>${escapeHtml(dimension.name)}</strong>
        <span>${dimension.score.toFixed(4)} 原始分</span>
      </div>
      ${dimension.factors.map((factor) => `
        <div class="factor-line ${factor.assumed ? "assumed" : ""}">
          <div class="factor-label">${escapeHtml(factor.name)}</div>
          <div class="factor-option" title="${escapeHtml(factor.label)} / ${escapeHtml(factor.source)}">${escapeHtml(factor.label)}</div>
          <div>${factor.score}分</div>
          <div>${factor.weightedScore.toFixed(4)}</div>
          <div><span class="source-tag">${escapeHtml(factor.source)}</span></div>
        </div>
      `).join("")}
    </div>
  `).join("");
}

function capabilityModeLabel(mode) {
  const labels = {
    cache: "本地缓存",
    live: "实时可用",
    configured: "已配置",
    failed: "已降级",
    not_configured: "未配置",
    local_anonymous: "本地匿名",
    unverified: "未验证"
  };
  return labels[mode] || mode || "未知";
}

function renderResearchStatus(result) {
  const plan = result.researchPlan || {};
  const evidence = result.evidencePack || {};
  const assessment = result.modelAssessment || {};
  const capabilities = result.capabilityStatus || {};
  const benchmark = plan.benchmarkCase || {};
  const summary = evidence.summary || {};
  const localCache = capabilities.localCache || {};
  const independentSearch = capabilities.independentSearch || {};
  const llm = capabilities.llm || {};
  const modelWebSearch = capabilities.modelWebSearch || {};
  const questions = (plan.questions || []).slice(0, 4);
  const evidenceItems = (evidence.items || []).slice(0, 6);
  const dynamicDimensions = (assessment.dynamicDimensions || []).slice(0, 6);
  const awaitingConsent = assessment.status === "awaiting_offline_fallback_consent";
  const statusText = awaitingConsent ? "待确认" : (assessment.fallbackUsed ? "基础研判" : "深化研判");
  const statusTone = awaitingConsent || assessment.fallbackUsed ? "warn" : "ok";
  if (!plan.questions && !evidence.items && !assessment.dynamicDimensions) return "";
  return `
    <section class="research-status">
      <div class="research-status-head">
        <div>
          <h3>分析资料状态</h3>
          <p>${escapeHtml(plan.strategy || "结合项目条件、标杆案例和外部资料形成研判。")}</p>
        </div>
        <span class="status-badge ${statusTone}">${statusText}</span>
      </div>
      <div class="research-metrics">
        <div><span>标杆案例</span><strong>${escapeHtml(benchmark.label || "通用预评估")}</strong></div>
        <div><span>参考资料</span><strong>${formatNumber(summary.total)}条</strong><small>${formatNumber(summary.cached)}既有 / ${formatNumber(summary.live)}更新</small></div>
        <div><span>外部检索</span><strong>${escapeHtml(capabilityModeLabel(independentSearch.mode))}</strong><small>${escapeHtml(independentSearch.reason || "可用时补充外部资料")}</small></div>
        <div><span>模型接入</span><strong>${escapeHtml(capabilityModeLabel(llm.mode))}</strong><small>${escapeHtml(llm.reason || "可用时生成综合研判")}</small></div>
        <div><span>模型联网</span><strong>${escapeHtml(capabilityModeLabel(modelWebSearch.mode))}</strong><small>${escapeHtml(modelWebSearch.reason || "低置信补充")}</small></div>
        <div><span>既有资料</span><strong>${escapeHtml(capabilityModeLabel(localCache.mode))}</strong><small>${formatNumber(localCache.evidenceCount)}条可用</small></div>
      </div>
      <div class="research-columns">
        <div>
          <h4>研究问题</h4>
          <ul>${questions.map((item) => `<li>${escapeHtml(item.question)}<span>${escapeHtml(item.priority)}</span></li>`).join("")}</ul>
        </div>
        <div>
          <h4>代表性资料</h4>
          <ul>${evidenceItems.map((item) => `<li>${escapeHtml(item.title)}<span>${escapeHtml(item.cached ? "既有" : "更新")} / ${escapeHtml(String(item.confidence ?? "待确认"))}</span></li>`).join("")}</ul>
        </div>
        <div>
          <h4>动态维度</h4>
          <ul>${dynamicDimensions.map((item) => `<li>${escapeHtml(item.name)}<span>${escapeHtml(String(item.confidence ?? "待确认"))}</span></li>`).join("")}</ul>
        </div>
      </div>
    </section>
  `;
}

function formatScoreNumber(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "--";
}

function factorOverviewText(factors = []) {
  return factors.map((factor) => {
    const name = factor.name || "未命名因子";
    const label = factor.label || "待补齐";
    const weighted = formatScoreNumber(factor.weightedScore, 4);
    return `${name}：${label}（加权${weighted}）`;
  }).join("；");
}

function factorSourceText(factors = []) {
  return factors.map((factor) => {
    const name = factor.name || "未命名因子";
    const source = factor.source || "规则评分表/项目输入";
    return `${name}：${source}`;
  }).join("；");
}

function renderScoreOverview(result) {
  const rawMax = result.scoreScale?.rawMax || "";
  const completeness = result.dataCompleteness || {};
  const summaryRows = [
    ["综合评分（百分制）", `${formatScoreNumber(result.scorePercent, 2)} 分`],
    ["原始加权分", `${formatScoreNumber(result.score, 4)}${rawMax ? ` / ${formatScoreNumber(rawMax, 4)}` : ""}`],
    ["联通等级", result.level || "待判定"],
    ["推荐方式", result.recommendation?.primary?.name || "待推荐"],
    ["数据完整度", `${completeness.done ?? 0}/${completeness.total ?? 0}`]
  ];
  const dimensionRows = (result.dimensions || []).map((dimension) => {
    const assumed = (dimension.factors || []).filter((factor) => factor.assumed).map((factor) => factor.name).filter(Boolean);
    return `
      <tr>
        <td>${escapeHtml(dimension.name || "")}</td>
        <td class="number-cell">${escapeHtml(formatScoreNumber(dimension.score, 4))}</td>
        <td>${escapeHtml(factorOverviewText(dimension.factors || []))}</td>
        <td>${escapeHtml(factorSourceText(dimension.factors || []))}</td>
        <td>${escapeHtml(assumed.length ? `含临时试算：${assumed.join("、")}` : "核心字段已取值")}</td>
      </tr>
    `;
  }).join("");

  return `
    <section class="report-score-overview">
      <h2>评分总览</h2>
      <div class="report-score-grid">
        <table class="report-score-table">
          <tbody>
            ${summaryRows.map(([label, value]) => `
              <tr>
                <th>${escapeHtml(label)}</th>
                <td>${escapeHtml(value)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
        <table class="report-score-table dimension-overview-table">
          <thead>
            <tr>
              <th>评分维度</th>
              <th>加权得分</th>
              <th>主要因子取值</th>
              <th>来源依据</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>${dimensionRows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderReport(result) {
  const node = $("#reportPreview");
  const primary = result.recommendation.primary;
  const reportSections = result.clientReport?.length ? result.clientReport : result.report;
  const project = result.project || {};
  const station = project.station?.name ? `${project.station.name}站` : "目标车站";
  const projectName = project.name || "互联互通项目";
  const levelText = String(result.level || "").includes("尽连")
    ? "建议推进联通"
    : (String(result.level || "").includes("可连") ? "具备联通条件" : result.level);
  const plainConclusion = `结论：${levelText}，优先采用${primary.name}。`;
  node.className = "report-preview";
  node.innerHTML = `
    <article class="report-document">
      <header class="report-title-block">
        <h1>${escapeHtml(projectName)}综合评估报告</h1>
        <p class="report-lead">本报告围绕${escapeHtml(station)}与周边地块的互联互通必要性、推荐联通方式、设计控制要求和实施建议进行综合研判，结论面向方案决策和后续深化设计使用。</p>
        <div class="report-conclusion">
          <strong>${escapeHtml(plainConclusion)}</strong>
          <p>${escapeHtml(result.policy)} 综合评分为 ${result.scorePercent.toFixed(1)} 分，规则评分、等级和推荐方式作为本次判断的锁定结论，报告正文在此基础上展开设计解释和实施建议。</p>
        </div>
      </header>
      ${renderScoreOverview(result)}
      ${reportSections.map((section, index) => `
        <article class="report-section">
          <h2>${index + 1}. ${escapeHtml(section.title)}</h2>
          <p>${escapeHtml(section.content)}</p>
        </article>
      `).join("")}
    </article>
  `;
}

function projectFieldGaps(project) {
  const checks = [
    ["项目附件", "attachments", "补齐控规图则、规划条件、概念方案和附件目录。"],
    ["邻近出入口", "station.nearbyExit", "明确拟接驳的车站出入口编号和空间位置。"],
    ["接口条件", "station.interfaceCondition", "补齐接口位置、标高、非付费区条件和运营界面。"],
    ["规划指标", "parcel.planningIndicators", "补齐容积率、建筑密度、限高、用地边界等规划条件。"],
    ["地下空间说明", "parcel.undergroundDescription", "补齐地下层数、公共开放功能和可接驳空间。"],
    ["特殊约束", "parcel.constraints", "补齐管线、风貌、时序、产权和施工界面约束。"]
  ];
  return checks
    .filter(([, path]) => !getNested(project, path))
    .map(([name, , message]) => ({ type: "项目字段", name, message, status: "待补齐", action: "由项目提资补充" }));
}

function knowledgeGaps() {
  const sources = unparsedSources();
  const items = [];
  const legacyDocs = sources.filter((item) => item.parseStatus === "unparsed");
  const images = sources.filter((item) => item.parseStatus === "metadata_only");
  const ignored = sources.filter((item) => item.parseStatus === "ignored");

  if (legacyDocs.length) {
    items.push({
      type: "资料",
      name: `文档格式处理 ${legacyDocs.length} 项`,
      message: legacyDocs.map((item) => item.path.split(/[\\/]/).pop()).join("、"),
      status: "待补齐",
      action: "转换为可检索文档后纳入分析依据"
    });
  }
  if (images.length) {
    items.push({
      type: "资料",
      name: `示意图语义标注 ${images.length} 张`,
      message: "联通示意图仍需补充方案类型、适用场景和限制条件。",
      status: "待补齐",
      action: "补充图像语义标注后用于方案比选"
    });
  }
  if (ignored.length) {
    items.push({
      type: "资料",
      name: `非业务文件 ${ignored.length} 项`,
      message: "临时文件不参与项目研判。",
      status: "无需补齐",
      action: "可继续忽略"
    });
  }
  return items;
}

function buildCompletionItems(result = state.currentResult) {
  const project = result?.project || state.currentProject || collectProject();
  const scoring = (result?.missing || []).map((item) => ({
    type: "评分字段",
    name: item.name,
    message: item.message,
    status: "待补齐",
    action: "补齐后重新运行评估"
  }));
  return [...scoring, ...projectFieldGaps(project), ...knowledgeGaps()];
}

function buildDeliveryStatusGroups() {
  const completionItems = buildCompletionItems();
  const actionableGaps = completionItems.filter((item) => item.status !== "无需补齐");
  const parsedSources = sourceManifest().filter((item) => item.parseStatus === "parsed").length;
  const metadataSources = sourceManifest().filter((item) => item.parseStatus === "metadata_only").length;
  const unparsedCount = unparsedSources().filter((item) => item.parseStatus !== "ignored").length;
  const projectGapCount = actionableGaps.filter((item) => item.type === "项目字段" || item.type === "评分字段").length;
  const materialGapCount = actionableGaps.filter((item) => item.type === "资料").length;
  const platform = state.bootstrap?.platformCapabilities || {};
  const generatedImage = platform.generatedImage || {};
  const accounts = platform.accounts || {};
  const deployment = platform.deployment || {};

  return [
    {
      key: "done",
      title: "已完成",
      count: 6,
      tone: "ok",
      summary: `已接入 ${formatNumber(parsedSources)} 个全文资料，${formatNumber(metadataSources)} 个图像/示意资料可供参考。`,
      items: [
        "项目录入、保存、读取、删除均可正常使用。",
        "评估结论、推荐方案和报告预览可一键生成。",
        "依据资料检索和报告导出可支撑日常方案沟通。"
      ]
    },
    {
      key: "external",
      title: "需外部资料",
      count: actionableGaps.length,
      tone: "warn",
      summary: `当前项目共有 ${formatNumber(actionableGaps.length)} 项建议补充，其中项目字段 ${formatNumber(projectGapCount)} 项，支撑资料 ${formatNumber(materialGapCount)} 项。`,
      items: actionableGaps.slice(0, 3).map((item) => `${item.name}：${item.action || item.message}`)
    },
    {
      key: "platform",
      title: "平台能力",
      count: [generatedImage.enabled, accounts.enabled, deployment.validation?.ok].filter(Boolean).length,
      tone: deployment.validation?.ok === false ? "warn" : "muted",
      summary: `生成图 ${capabilityModeLabel(generatedImage.mode)}，账号 ${capabilityModeLabel(accounts.mode)}，服务 ${deployment.host || "--"}:${deployment.port || "--"}。`,
      items: [
        `生成图 provider：${generatedImage.provider || "disabled"}`,
        `导出目录：${deployment.exportDir || "exports"}`
      ]
    },
    {
      key: "manual",
      title: "不能自动完成",
      count: 4,
      tone: "muted",
      summary: "以下事项需要项目团队结合正式资料和工程条件进一步确认。",
      items: [
        "控规图则、规划条件、接口标高、管线和产权边界需外部提资确认。",
        "CAD/DWG/BIM 读取、施工图审查、工程级平剖面图不属于一期自动生成范围。",
        `扫描件或示意图需人工补充语义后再用于方案深化，当前待处理 ${formatNumber(unparsedCount)} 项。`
      ]
    }
  ];
}

function renderDeliveryStatus() {
  const groups = buildDeliveryStatusGroups();
  const gapCount = groups.find((item) => item.key === "external")?.count || 0;
  const badge = $("#deliveryStatusBadge");
  badge.textContent = gapCount ? `${formatNumber(gapCount)} 项待外部补齐` : "试点资料已齐";
  badge.className = gapCount ? "pill warn" : "pill";

  $("#deliveryStatusBoard").innerHTML = groups.map((group) => `
    <article class="delivery-status-card ${group.tone}">
      <div class="delivery-status-head">
        <span>${escapeHtml(group.title)}</span>
        <strong>${formatNumber(group.count)}</strong>
      </div>
      <p>${escapeHtml(group.summary)}</p>
      <ul>${group.items.length
        ? group.items.slice(0, 2).map((item) => `<li>${escapeHtml(item)}</li>`).join("")
        : "<li>暂无需要外部补齐的项目，导出前仍建议人工复核。</li>"
      }</ul>
    </article>
  `).join("");
}

function modelJudgement(result = state.currentResult) {
  return result?.modelJudgement || {};
}

function modelDifference(result = state.currentResult) {
  return result?.modelRuleDifference || {};
}

function modelQuality(result = state.currentResult) {
  return result?.modelQuality || {};
}

function renderModelList(node, items, className) {
  if (!node) return;
  if (!items?.length) {
    node.innerHTML = `<div class="empty-state">暂无模型条目。</div>`;
    return;
  }
  node.innerHTML = items.map((item) => `
    <article class="${className}">
      <strong>${escapeHtml(item.title || item.name || item.id)}</strong>
      <p>${escapeHtml(item.detail || item.reason || item.reviewLabel || "")}</p>
      <span>${escapeHtml(item.severity || item.priority || item.reviewLabel || "复核")}</span>
    </article>
  `).join("");
}

function renderModelJudgement(result = state.currentResult) {
  const judgement = modelJudgement(result);
  const difference = modelDifference(result);
  const quality = modelQuality(result);
  const title = $("#modelJudgementTitle");
  const reason = $("#modelJudgementReason");
  const confidence = $("#modelConfidence");
  const differencePanel = $("#modelDifferencePanel");
  if (!title || !reason || !confidence || !differencePanel) return;
  if (!result || !judgement.level) {
    title.textContent = "模型研判待运行";
    reason.textContent = "运行评估后展示模型最终结论、覆盖理由和置信度。";
    confidence.textContent = "--";
    differencePanel.textContent = "规则基线与模型差异将在运行后展示。";
    renderModelList($("#modelRiskList"), [], "model-risk-item");
    renderModelList($("#modelFundingList"), [], "model-funding-item");
    return;
  }
  title.textContent = `模型建议：${judgement.level}，${judgement.recommendedType}`;
  reason.textContent = judgement.reason || "模型已基于项目资料生成综合判断。";
  confidence.textContent = `${Math.round(Number(judgement.confidence || 0) * 100)}%`;
  const labels = [...new Set([...(difference.reviewLabels || []), ...(quality.labels || [])].filter(Boolean))];
  differencePanel.innerHTML = `
    <strong>规则基线：${escapeHtml(difference.ruleLevel || result.level)} / ${escapeHtml(difference.ruleRecommendedType || result.recommendation?.primary?.name || "")}</strong>
    <span>模型结论：${escapeHtml(difference.modelLevel || judgement.level)} / ${escapeHtml(difference.modelRecommendedType || judgement.recommendedType)}</span>
    <p>${escapeHtml(difference.reason || judgement.overrideReason || "模型结论与规则基线一致。")}</p>
    <span>复核标签：${labels.map((label) => `<b>${escapeHtml(label)}</b>`).join("")}</span>
  `;
  renderModelList($("#modelRiskList"), judgement.riskItems || [], "model-risk-item");
  renderModelList($("#modelFundingList"), judgement.fundingRequests || [], "model-funding-item");
}

function renderReportModes(result = state.currentResult) {
  const tabs = $("#reportModeTabs");
  const summary = $("#reportModeSummary");
  if (!tabs || !summary) return;
  const modes = result?.reportModes || [];
  if (!modes.length) {
    tabs.innerHTML = "";
    summary.textContent = "运行评估后可切换客户正式版、专家附录版和领导汇报版。";
    return;
  }
  const active = state.reportMode || modes[0].id;
  tabs.innerHTML = modes.map((mode) => `
    <button type="button" data-report-mode="${escapeHtml(mode.id)}" class="${mode.id === active ? "active" : ""}">
      ${escapeHtml(mode.name)}
    </button>
  `).join("");
  const selected = modes.find((mode) => mode.id === active) || modes[0];
  summary.textContent = `${selected.name}：${selected.tone}。重点：${selected.focus}。`;
}

function renderDiagramBrief(result = state.currentResult) {
  const brief = result?.diagramBrief || {};
  const title = $("#diagramBriefTitle");
  const node = $("#diagramBriefSvg");
  if (!title || !node) return;
  title.textContent = brief.title || "推荐联通路径示意";
  const nodes = brief.nodes || [];
  const edges = brief.edges || [];
  if (!nodes.length || !edges.length) {
    node.innerHTML = `<div class="empty-state">运行评估后生成示意图 brief。</div>`;
    return;
  }
  const byId = Object.fromEntries(nodes.map((item) => [item.id, item]));
  node.innerHTML = `
    <svg viewBox="0 0 560 280" role="img" aria-label="${escapeHtml(brief.title || "推荐联通路径示意")}">
      <rect x="18" y="24" width="524" height="216" rx="8" class="diagram-bg"></rect>
      ${edges.map((edge) => {
        const from = byId[edge.from] || nodes[0];
        const to = byId[edge.to] || nodes[nodes.length - 1];
        const label = edge.label?.includes("推荐") ? edge.label : `推荐：${edge.label || "联通路径"}`;
        return `<g>
          <path d="M ${from.x} ${from.y} C ${from.x + 90} ${from.y - 70}, ${to.x - 90} ${to.y + 70}, ${to.x} ${to.y}" class="diagram-path"></path>
          <text x="${(from.x + to.x) / 2 - 58}" y="${(from.y + to.y) / 2 - 38}" class="diagram-label">${escapeHtml(label)}</text>
        </g>`;
      }).join("")}
      ${nodes.map((item) => `
        <g>
          <circle cx="${item.x}" cy="${item.y}" r="34" class="diagram-node ${escapeHtml(item.type || "")}"></circle>
          <text x="${item.x}" y="${item.y + 4}" text-anchor="middle" class="diagram-node-label">${escapeHtml(item.label)}</text>
        </g>
      `).join("")}
      ${(brief.annotations || []).map((item, index) => `
        <text x="52" y="${226 + index * 18}" class="diagram-note">${escapeHtml(item.text)}</text>
      `).join("")}
    </svg>
  `;
}

function renderDashboardHero() {
  const result = state.currentResult;
  const project = result?.project || state.currentProject || collectProject();
  const station = project.station || {};
  const parcel = project.parcel || {};
  const projectName = project.name || "待选择项目";
  const meta = [
    station.name ? `${station.name}站` : "车站待补齐",
    parcel.location || parcel.quadrant || "",
    project.projectCode || ""
  ].filter(Boolean).join(" / ");

  $("#currentProjectTitle").textContent = projectName;
  $("#currentProjectMeta").textContent = meta || "载入示例或选择已保存项目后生成评估摘要。";
  renderDashboardInputs(project);
  updateSchematicLinks(project);
  renderSchematicPreview(result);

  if (!result) {
    $("#dashboardScorePercent").textContent = "--";
    $("#dashboardLevel").textContent = "--";
    $("#dashboardType").textContent = "--";
    $("#dashboardPolicy").textContent = "运行评估后展示联通等级、推荐方式与主要判断依据。";
    $("#currentProjectBadge").textContent = "待运行";
    $("#currentProjectBadge").className = "pill muted";
    renderModelJudgement(null);
    renderReportModes(null);
    renderDiagramBrief(null);
    renderDashboardDimensions(null);
    renderDashboardReportOutline(null);
    return;
  }

  $("#dashboardScorePercent").textContent = `${result.scorePercent.toFixed(1)} / 100`;
  $("#dashboardLevel").textContent = result.level;
  $("#dashboardType").textContent = result.recommendation.primary.name;
  $("#dashboardPolicy").textContent = `${result.policy} 命中规则：${result.recommendation.rule.reason}`;
  $("#currentProjectBadge").textContent = result.provisional ? "含待补齐" : "核心字段完整";
  $("#currentProjectBadge").className = result.provisional ? "pill warn" : "pill";
  renderModelJudgement(result);
  renderReportModes(result);
  renderDiagramBrief(result);
  renderDashboardDimensions(result);
  renderDashboardReportOutline(result);
}

function schematicUrl(project) {
  const params = new URLSearchParams();
  if (state.currentProjectId) params.set("projectId", state.currentProjectId);
  if (project?.station?.name) params.set("station", project.station.name);
  if (project?.name) params.set("project", project.name);
  const query = params.toString();
  return `/schematic/index.html${query ? `?${query}` : ""}`;
}

function updateSchematicLinks(project = state.currentProject) {
  const url = schematicUrl(project);
  const navLink = $("#schematicNavLink");
  const dashboardLink = $("#dashboardSchematicLink");
  if (navLink) navLink.href = url;
  if (dashboardLink) dashboardLink.href = url;
  const note = $("#dashboardSchematicNote");
  if (note) {
    const station = project?.station?.name || "当前车站";
    const name = project?.name || "当前地块";
    note.textContent = `当前关联：${station} / ${name}。出图页用于校准红线、站体、出入口和通道坐标。`;
  }
}

function renderSchematicPreview(result = state.currentResult) {
  const project = result?.project || state.currentProject || collectProject();
  const primary = result?.recommendation?.primary?.name || "推荐联通路径";
  const station = project?.station?.name || "目标车站";
  const exit = project?.station?.nearbyExit || "邻近出入口";
  const parcelName = project?.name || "目标地块";
  const stationNode = $("#summaryStationName");
  const channelNode = $("#summaryChannelName");
  const exitNode = $("#summaryExitName");
  const parcelNode = $("#summaryParcelName");
  if (stationNode) stationNode.textContent = station.endsWith("站") ? station : `${station}站`;
  if (channelNode) channelNode.textContent = primary;
  if (exitNode) exitNode.textContent = exit;
  if (parcelNode) parcelNode.textContent = parcelName;
}

function renderDashboardInputs(project) {
  const station = project.station || {};
  const parcel = project.parcel || {};
  const stationTypeLabels = {
    current_transfer: "现状换乘站",
    planned_transfer: "规划换乘站",
    normal: "一般站"
  };
  const items = [
    ["对象", `${station.name || "车站待补齐"} / ${project.name || "地块待选择"}`],
    ["位置", [parcel.location || parcel.quadrant, station.nearbyExit].filter(Boolean).join(" / ") || "待补齐"],
    ["属性", [station.line ? `${station.line}号线` : "", stationTypeLabels[station.stationType] || station.stationType, station.todLevel].filter(Boolean).join(" / ") || "待补齐"],
    ["规模", parcel.buildingArea ? `${formatNumber(parcel.buildingArea)}㎡，${parcel.functionalFormat || parcel.landUseText || "业态待补齐"}` : "待补齐"]
  ];
  const node = $("#dashboardInputSummary");
  if (!node) return;
  node.innerHTML = items.map(([label, value]) => `
    <div>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");
}

function renderDashboardDimensions(result) {
  const node = $("#dashboardDimensionTable");
  if (!node) return;
  if (!result) {
    node.className = "dimension-table empty-state";
    node.textContent = "运行评估后生成四类维度得分。";
    return;
  }
  node.className = "dimension-table";
  const raw = rawMax(result) || 1;
  const rows = result.dimensions.map((dimension) => {
    const percent = Math.max(0, Math.min(100, (dimension.score / raw) * 100));
    const factorText = dimension.factors.map((factor) => factor.name).join("、");
    return `
      <div class="dashboard-dimension-row">
        <div>
          <strong>${escapeHtml(dimension.name)}</strong>
          <span>${escapeHtml(factorText)}</span>
        </div>
        <b>${dimension.score.toFixed(2)}</b>
        <i><em style="width:${percent}%"></em></i>
      </div>
    `;
  }).join("");
  node.innerHTML = `
    <div class="dimension-head"><span>维度</span><span>原始得分</span></div>
    ${rows}
    <div class="dimension-total">
      <span>综合得分（满分100）</span>
      <strong>${result.scorePercent.toFixed(2)}</strong>
      <span class="status-badge ok">${escapeHtml(result.level)}</span>
    </div>
  `;
}

function renderDashboardReportOutline(result) {
  const node = $("#dashboardReportOutline");
  if (!node) return;
  if (!result) {
    node.className = "report-outline-grid empty-state";
    node.textContent = "报告大纲将在运行评估后生成。";
    return;
  }
  node.className = "report-outline-grid";
  node.innerHTML = result.report.slice(0, 6).map((section, index) => {
    const points = section.content
      .split(/[。；]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 3);
    return `
      <article>
        <span>${index + 1}</span>
        <h3>${escapeHtml(section.title)}</h3>
        <ul>${points.map((point) => `<li>${escapeHtml(clipText(point, 30))}</li>`).join("")}</ul>
      </article>
    `;
  }).join("");
}

function renderCompletionList(node, items, options = {}) {
  const visible = options.includeIgnored ? items : items.filter((item) => item.status !== "无需补齐");
  if (!visible.length) {
    node.className = "completion-list empty-state";
    node.textContent = "当前没有需要处理的补齐项。";
    return;
  }
  node.className = "completion-list";
  const limit = options.limit ?? visible.length;
  const clipped = visible.slice(0, limit);
  const extra = visible.length - clipped.length;
  node.innerHTML = clipped.map((item) => `
      <div class="completion-item">
        <div>
          <strong>${escapeHtml(item.name)}</strong>
          <p>${escapeHtml(item.message)}</p>
          <small>${escapeHtml(item.action || "")}</small>
        </div>
        <span class="status-badge ${item.status === "无需补齐" ? "muted" : "warn"}">${escapeHtml(item.type)} / ${escapeHtml(item.status)}</span>
      </div>
    `).join("") + (extra > 0 ? `<div class="completion-more">另有 ${formatNumber(extra)} 项，进入报告页查看完整清单。</div>` : "");
}

function renderMissing(result) {
  renderCompletionList($("#missingList"), buildCompletionItems(result));
}

function renderRuleSummary() {
  const factorCount = state.bootstrap.factors.dimensions.reduce((sum, item) => sum + item.factors.length, 0);
  const typeCount = state.bootstrap.rules.connectionTypes.length;
  $("#ruleSummary").innerHTML = `
    <div class="rule-stat"><strong>${formatNumber(factorCount)}</strong><span>评分因子覆盖区位、客流、功能与开发强度。</span></div>
    <div class="rule-stat"><strong>${formatNumber(typeCount)}</strong><span>联通方式，按地下、地面、空中分类推荐。</span></div>
    <div class="rule-stat"><strong>复核</strong><span>导出前建议结合正式设计条件进行人工确认。</span></div>
  `;
}

function renderTrace(result) {
  const gradeRules = state.bootstrap.factors.grading
    .map((item) => `${item.level}: ${item.percentMin ?? "-∞"} ~ ${item.percentMax ?? "+∞"}分`)
    .join("；");
  const rule = result.recommendation.rule;
  const assumedCount = result.dimensions.flatMap((item) => item.factors).filter((item) => item.assumed).length;
  $("#ruleSummary").innerHTML = `
    <div class="rule-stat"><strong>${result.scorePercent.toFixed(1)}</strong><span>百分制评分命中：${escapeHtml(result.level)}。阈值：${escapeHtml(gradeRules)}</span></div>
    <div class="rule-stat"><strong>${assumedCount}</strong><span>当前临时试算因子数，为 0 表示核心评分字段完整。</span></div>
    <div class="rule-stat"><strong>${escapeHtml(result.recommendation.primary.name)}</strong><span>命中规则：${escapeHtml(rule.when)}。理由：${escapeHtml(rule.reason)}</span></div>
  `;
}

function renderDashboard() {
  const summary = state.bootstrap?.knowledgeCatalog?.summary || {};
  const setIfPresent = (selector, value) => {
    const node = $(selector);
    if (node) node.textContent = value;
  };
  setIfPresent("#knowledgeSourceCount", formatNumber(summary.sourceCount));
  setIfPresent("#knowledgeChunkCount", formatNumber(summary.chunkCount));
  setIfPresent("#stationIndexCount", formatNumber(summary.stationIndexCount));
  setIfPresent("#globalGapCount", formatNumber(buildCompletionItems().filter((item) => item.status !== "无需补齐").length));
  renderDashboardHero();
  renderDeliveryStatus();
  renderDataReadiness();
  renderCompletionList($("#completionBacklog"), buildCompletionItems(), { limit: 5 });
}

function renderDataReadiness() {
  const categories = [
    ["work_plan", "评估框架"],
    ["feedback", "反馈提资"],
    ["scoring", "评分依据"],
    ["input_schema", "录入标准"],
    ["ridership", "客流"],
    ["station_interface", "出入口接口"],
    ["station_amenities", "周边配套"],
    ["design_guidance", "设计导则"]
  ];
  $("#dataReadiness").innerHTML = categories.map(([category, label]) => {
    const sources = sourceManifest().filter((item) => item.category === category);
    const parsed = sources.filter((item) => item.parseStatus === "parsed").length;
    const partial = sources.filter((item) => item.parseStatus === "metadata_only").length;
    const status = sources.length && parsed + partial === sources.length ? "已入库" : "需补齐";
    return `
      <div class="readiness-item">
        <div><strong>${label}</strong><span>${parsed}/${sources.length} 已纳入${partial ? `，${partial} 待深化` : ""}</span></div>
        <span class="status-badge ${status === "已入库" ? "ok" : "warn"}">${status}</span>
      </div>
    `;
  }).join("");
}

function renderKnowledgeSummary() {
  const catalog = state.bootstrap.knowledgeCatalog || {};
  const summary = catalog.summary || {};
  const status = catalog.sourceStatus || {};
  const builtAt = catalog.builtAt ? catalog.builtAt.slice(0, 10) : "";
  $("#knowledgeFreshness").textContent = builtAt ? `${builtAt} 构建` : "已构建";
  $("#knowledgeSummary").innerHTML = `
    <div><strong>${formatNumber(summary.sourceCount)}</strong><span>支撑资料</span></div>
    <div><strong>${formatNumber(summary.chunkCount)}</strong><span>可检索内容</span></div>
    <div><strong>${formatNumber(summary.stationIndexCount)}</strong><span>站点覆盖</span></div>
    <div><strong>${formatNumber(status.metadata_only || 0)}</strong><span>示意资料</span></div>
  `;
}

function renderSourceManifest() {
  const body = $("#sourceManifestBody");
  if (body) body.innerHTML = "";
  const gapNode = $("#knowledgeGapList");
  if (gapNode) gapNode.textContent = "";
}

function renderKnowledgeResults(results, totalCount, query) {
  const node = $("#knowledgeResults");
  if (!results.length) {
    node.className = "knowledge-results empty-state";
    node.textContent = `未检索到“${query}”相关资料。`;
    return;
  }
  node.className = "knowledge-results";
  node.innerHTML = `
    <div class="knowledge-result-meta">检索到 ${formatNumber(totalCount)} 条相关内容，当前展示 ${results.length} 条。</div>
    ${results.map((item) => `
      <article class="knowledge-result">
        <div class="knowledge-result-head">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(categoryName(item.category))} / ${escapeHtml(readableKind(item.kind))}</span>
        </div>
        <p>${escapeHtml(clipText(item.text, 150))}</p>
        <div class="knowledge-source"><span>${escapeHtml(categoryName(item.category))}</span><span>相关度 ${formatNumber(item.score)}</span></div>
      </article>
    `).join("")}
  `;
}

async function searchKnowledge() {
  const input = $("#knowledgeSearchInput");
  const button = $("#knowledgeSearchBtn");
  const query = input.value.trim();
  if (!query) {
    $("#knowledgeResults").className = "knowledge-results empty-state";
    $("#knowledgeResults").textContent = "输入关键词后检索与项目研判相关的支撑内容。";
    return;
  }
  button.disabled = true;
  button.textContent = "检索中";
  $("#knowledgeResults").className = "knowledge-results empty-state";
  $("#knowledgeResults").textContent = "正在检索支撑资料...";
  try {
    const response = await api(`/api/knowledge/search?q=${encodeURIComponent(query)}&limit=50`);
    const category = $("#knowledgeCategoryFilter").value;
    const results = category ? (response.results || []).filter((item) => item.category === category) : (response.results || []);
    state.lastKnowledgeResults = results;
    renderKnowledgeResults(results.slice(0, 5), results.length || response.count || 0, query);
  } catch (error) {
    $("#knowledgeResults").className = "knowledge-results empty-state";
    $("#knowledgeResults").textContent = `检索失败：${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "检索";
  }
}

function buildMarkdown(result) {
  const title = result.project.name || "互联互通评估报告";
  const sections = result.report.map((section, index) => `## ${index + 1}. ${section.title}\n\n${section.content}`).join("\n\n");
  const rawMax = result.scoreScale?.rawMax || "";
  return `# ${title}\n\n综合评分（百分制）：${result.scorePercent.toFixed(2)}分\n\n原始加权分：${result.score.toFixed(4)}${rawMax ? ` / ${Number(rawMax).toFixed(4)}` : ""}\n\n联通等级：${result.level}\n\n推荐方式：${result.recommendation.primary.name}\n\n${sections}\n`;
}

function exportDownloadUrl(item = {}) {
  if (item.downloadUrl) return item.downloadUrl;
  if (item.relativePath) return `/${item.relativePath.replaceAll("\\", "/")}`;
  return "#";
}

async function exportReport() {
  try {
    if (!state.currentResult) await runEvaluation();
    const project = state.currentResult?.project || state.currentProject || collectProject();
    const options = researchOptions();
    const body = Object.keys(options).length ? { project, researchOptions: options } : { project };
    const response = await api("/api/export", {
      method: "POST",
      body: JSON.stringify(body)
    });
    const files = response.export.files || [];
    $("#exportPathValue").textContent = files.length ? `${files.length} 个文件已生成` : response.export.relativePath;
    $("#exportFiles").innerHTML = files.map((item) => {
      const href = item.downloadUrl || exportDownloadUrl(item);
      return `<a href="${href}" title="${escapeHtml(item.relativePath)}">${escapeHtml(item.filename)}</a>`;
    }).join("");
    await refreshExports();

    const first = files.find((item) => item.filename.endsWith("-formal-report.docx")) || files[0];
    if (first) {
      const link = document.createElement("a");
      link.href = first.downloadUrl || exportDownloadUrl(first);
      link.download = first.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } else {
      const markdown = buildMarkdown(state.currentResult);
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = response.export.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }
  } catch (error) {
    $("#exportPathValue").textContent = `导出失败：${error.message}`;
    $("#exportFiles").innerHTML = "";
    throw error;
  }
}

function renderExportHistory() {
  const node = $("#exportHistory");
  if (!state.exports.length) {
    node.className = "export-history empty-state";
    node.textContent = "暂无导出文件。";
    return;
  }
  node.className = "export-history";
  node.innerHTML = state.exports.slice(0, 12).map((item) => `
    <a href="${item.downloadUrl || exportDownloadUrl(item)}" class="export-row">
      <span>${escapeHtml(item.kind || "导出文件")}</span>
      <strong>${escapeHtml(item.filename)}</strong>
      <small>${escapeHtml(item.updatedAt || "")}</small>
    </a>
  `).join("");
}

function showView(viewName) {
  const target = PAGE_META[viewName] ? viewName : "dashboard";
  for (const view of $$(".view")) view.classList.toggle("active", view.id === target);
  for (const link of $$("[data-view-link]")) link.classList.toggle("active", link.dataset.viewLink === target);
  $("#pageTitle").textContent = PAGE_META[target][0];
  $("#pageSubtitle").textContent = PAGE_META[target][1];
  if (location.hash !== `#${target}`) history.replaceState(null, "", `#${target}`);
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
}

function updateActionStates() {
  const selectedId = $("#projectSelect").value;
  $("#deleteProjectBtn").disabled = !selectedId || !state.projects.some((item) => item.id === selectedId);
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-report-mode]");
    if (!button) return;
    state.reportMode = button.dataset.reportMode;
    renderReportModes(state.currentResult);
  });
  for (const link of $$("[data-view-link]")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showView(link.dataset.viewLink);
    });
  }
  $("#loadDemoBtn").addEventListener("click", async () => {
    fillProject(selectedDemo());
    clearEvaluationOutput("模板已载入。请点击“运行评估”，系统会调用模型生成完整报告。");
    showView("assessment");
  });
  $("#evaluateBtn").addEventListener("click", async () => {
    await runEvaluation();
    showView("reporting");
  });
  $("#saveProjectBtn").addEventListener("click", saveProject);
  $("#deleteProjectBtn").addEventListener("click", deleteCurrentProject);
  $("#saveStationMemoryBtn").addEventListener("click", saveStationMemory);
  $("#applyStationMemoryBtn").addEventListener("click", applyStationMemory);
  $("#exportProjectIntakeBtn").addEventListener("click", exportProjectIntake);
  $("#importProjectIntakeBtn").addEventListener("click", () => $("#importProjectIntakeFile").click());
  $("#importProjectIntakeFile").addEventListener("change", (event) => importProjectIntakeFile(event.target.files?.[0]));
  $("#exportBtn").addEventListener("click", exportReport);
  $("#projectSelect").addEventListener("change", loadSavedProject);
  $('[name="station.name"]').addEventListener("input", queueStationSearch);
  $('[name="station.name"]').addEventListener("change", autofillStationByName);
  bindStationAutofillOwnership();
  $("#knowledgeSearchBtn").addEventListener("click", searchKnowledge);
  $("#knowledgeSearchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchKnowledge();
    }
  });
  $("#knowledgeCategoryFilter").addEventListener("change", () => {
    const query = $("#knowledgeSearchInput").value.trim();
    if (query) searchKnowledge();
  });
}

async function init() {
  state.bootstrap = await api("/api/bootstrap");
  populateBootstrap();
  bindEvents();
  fillProject(selectedDemo());
  clearEvaluationOutput("请选择项目或载入模板，然后点击“运行评估”生成完整报告。");
  showView((location.hash || "#dashboard").slice(1));
}

init().catch((error) => {
  console.error(error);
  $("#recommendationBody").textContent = `系统初始化失败：${error.message}`;
});
