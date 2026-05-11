const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const projectsPath = path.join(root, "data", "projects.json");
const payload = JSON.parse(fs.readFileSync(projectsPath, "utf8"));
const projects = payload.projects || [];

function fail(message, detail = {}) {
  console.error(JSON.stringify({ ok: false, message, detail }, null, 2));
  process.exit(1);
}

const sample = projects.find((item) => item.id === "station-乐桥") || projects[0];
if (!sample) {
  fail("缺少可验收项目样本");
}

const result = sample.result || {};
const report = result.report || [];
const llmContext = result.llmReviewContext || {};
const references = llmContext.referenceBasis || [];
const dimensions = llmContext.dimensionJudgement || [];
const alternatives = llmContext.schemeComparison || [];
const risks = llmContext.riskAndReviewPoints || [];

if (report.length < 10) {
  fail("评价报告章节数量不足，不能支撑综合研判", { sectionCount: report.length });
}

const requiredTitles = ["评价口径与引用依据", "多维度评分拆解", "方案比选", "风险约束", "LLM综合判断框架"];
const titles = report.map((section) => section.title || "");
for (const title of requiredTitles) {
  if (!titles.some((item) => item.includes(title))) {
    fail("评价报告缺少必要章节", { missingTitle: title, titles });
  }
}

if (references.length < 6) {
  fail("LLM综合判断上下文缺少足够规则/资料引用", { referenceCount: references.length, references });
}

if (dimensions.length < 4) {
  fail("LLM综合判断上下文缺少四大维度拆解", { dimensions });
}

if (alternatives.length < 3) {
  fail("LLM综合判断上下文缺少推荐方案与备选方案比选", { alternatives });
}

if (risks.length < 5) {
  fail("LLM综合判断上下文缺少风险与复核要点", { risks });
}

if (!Array.isArray(llmContext.suggestedOutputSchema) || llmContext.suggestedOutputSchema.length < 5) {
  fail("LLM综合判断上下文缺少输出结构约束", { suggestedOutputSchema: llmContext.suggestedOutputSchema });
}

console.log(JSON.stringify({
  ok: true,
  project: sample.project?.name,
  sectionCount: report.length,
  referenceCount: references.length,
  dimensionCount: dimensions.length,
  schemeCount: alternatives.length,
  riskCount: risks.length,
  outputSchema: llmContext.suggestedOutputSchema
}, null, 2));
