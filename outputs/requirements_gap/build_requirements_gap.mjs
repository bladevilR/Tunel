import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const workbook = Workbook.create();

const palette = {
  dark: "#1F4E78",
  blue: "#D9EAF7",
  lightBlue: "#EEF6FC",
  green: "#E2F0D9",
  amber: "#FFF2CC",
  red: "#FCE4D6",
  gray: "#F2F2F2",
  white: "#FFFFFF",
  text: "#1F1F1F",
};

const gaps = [
  [1, "评分模型", "最终评分口径与权重版本", "P0-必须", "一期MVP", "现有 Excel、样例报告、工作方案存在口径差异", "区位/交通权重、出口衔接指标、一般站赋值、客流口径、用地功能最高分等需要确定唯一版本。", "若不统一，系统输出分值与报告样例可能不一致，后续验收容易产生争议。", "确认最终指标体系、权重、赋值标准、等级阈值，并形成《联通必要性评价模型口径确认表》。", "专业牵头方/甲方", "可先按样例报告口径反推一版规则，并列明差异待确认", "最高优先级"],
  [2, "站点数据", "完整站点基础数据库", "P0-必须", "一期MVP", "仅有 TOD 级别、站名、线路等基础整理", "缺站点功能类型、换乘属性、出入口数量、客流、建设状态、是否重点区域/古城/敏感区等字段。", "无法自动完成站点侧赋值和场景判断，只能依赖人工录入。", "补充全线网站点基础数据表，明确字段口径、数据来源、更新时间。", "甲方/运营或规划数据部门", "可先设计字段模板并支持人工录入", "影响自动化程度"],
  [3, "输入标准", "地块信息标准输入表", "P0-必须", "一期MVP", "工作方案中仅描述输入方向，未形成表单字段", "缺地块业态、主导功能、建筑面积口径、地下空间类型、距离/圈层、邻近出入口、接口条件、特殊约束等标准字段。", "前端表单、算法赋值和报告章节无法稳定对应。", "形成《地块信息输入字段表》，定义必填/选填、字段类型、枚举值、单位和校验规则。", "甲方专业组+开发方", "可先按资料和样例报告设计初版字段表", "一期启动前应确认"],
  [4, "客流数据", "站点客流与换乘数据口径", "P0-必须", "一期MVP", "样例报告使用日均进出站、峰小时等，Excel 使用日均进站量", "缺统一客流指标、统计周期、现状/远期口径、数据缺失时的默认处理规则。", "出行客流赋值会偏差，且难以解释模型依据。", "确认使用日均进站量、日均进出站量或高峰小时量；补充对应阈值和换算规则。", "甲方/运营数据部门", "可在系统中预留多口径字段和人工覆盖", "与评分模型强相关"],
  [5, "空间条件", "出入口、象限、接口与建设条件数据", "P0-必须", "一期MVP", "样例报告中有接口预留、邻近出入口等描述，但未形成统一数据表", "缺各站出入口位置、数量、象限、非付费区接口、接口标高、是否预留、现状障碍等。", "会影响出口衔接评分、联通方式推荐和技术可行性判断。", "补充站点接口条件表，至少覆盖一期试点站点。", "甲方/设计或建设管理部门", "可先设置人工填报字段，试点站点优先补齐", "建议先小范围试点"],
  [6, "规则库", "设计导则与细则结构化规则库", "P0-必须", "一期MVP", "PDF/Word 为自然语言条文，尚未拆成机器可执行规则", "强制性条文、引导性条文、参数值、适用场景、禁用条件、来源条款未结构化。", "报告容易泛化，合规性说明难以追溯来源。", "拆分为规则编号、规则类型、适用条件、参数值、推荐值、禁用条件、来源文件和条款。", "开发方初拆+甲方专业复核", "可先完成初版知识库和规则表", "专业复核是关键"],
  [7, "方案选型", "联通方式选型规则", "P1-重要", "一期MVP", "已有三大类八种方式，但适用分支较粗", "不同站点类型、地块业态、距离、建设状态、古城保护、既有改造等场景下的优先级和禁用条件不够细。", "推荐方案可能正确性不稳定，难以形成可解释比选。", "建立地下主通道、地下次通道、下沉广场、地下中庭、地面步行道、风雨连廊、高架连廊/天桥的选型矩阵。", "甲方专业组+开发方", "可先根据样例和导则形成初版矩阵", "影响方案建议质量"],
  [8, "报告输出", "标准化报告模板与段落规则", "P1-重要", "一期MVP", "已有两份样例报告，但不是机器模板", "缺固定章节、字段映射、计算表格式、结论句式、方案比选表、合规清单、导出格式要求。", "生成报告风格可能不统一，修改成本高。", "形成 Word 报告模板和章节字段映射表，明确必填内容和可变段落。", "开发方", "可直接整理一版并生成样例", "可由我方先行"],
  [9, "测试验收", "标准测试用例库", "P1-重要", "一期MVP", "目前只有两份参考报告", "缺必连、尽连、可连、不连、临界值、特殊场景、不同业态等测试样例及预期答案。", "无法证明模型准确率和报告质量，验收容易主观化。", "至少形成 20-30 组测试用例，包含输入条件、预期等级、推荐方式、关键依据。", "甲方专业组+开发方", "可先编制 8-10 个样例，甲方补充和确认", "验收核心材料"],
  [10, "资料管理", "资料版本与优先级清单", "P1-重要", "一期MVP", "文件包含过程稿、修改稿、节选稿、不同日期版本", "缺最高优先级资料、最新版、仅参考资料、冲突处理原则。", "知识库可能引用过期或低优先级内容。", "建立《资料版本清单》，标注正式/参考/废止、版本日期、优先级、维护人。", "甲方", "可先按现有文件整理初版清单", "减少后续扯皮"],
  [11, "特殊场景", "例外规则与豁免条件", "P1-重要", "一期增强", "工作方案提到古城、文保、遗址、特殊地质、分期建设等，但规则未落表", "缺特殊场景识别字段、调整规则、禁止条件、豁免条件和审批提示。", "常规场景可跑，但复杂项目容易给出不合规建议。", "形成特殊场景规则表，并在系统输出中单独提示风险。", "甲方专业组", "可先做风险提示框架", "可作为一期增强项"],
  [12, "成果边界", "一期/二期功能边界与验收指标", "P1-重要", "项目管理", "方案中近期和远期目标都有，但未形成开发边界", "文字报告、图纸读取、BIM审查、效果图生成混在同一叙述中，容易扩大一期范围。", "影响报价、排期、验收和责任划分。", "明确一期仅做评估+推荐+报告生成；二期再做图纸/BIM解析和审查。同步定义验收指标。", "甲方/项目管理方", "可起草边界说明", "建议提报时重点写清"],
  [13, "图纸资料", "CAD/DWG/DXF/总图样例与图层标准", "P2-二期", "二期", "当前仅有 PNG 示意图，无可解析工程图纸", "缺真实总图、地库图、联通通道平面、图层命名、图纸比例、坐标和人工审查结论。", "无法稳定实现图纸读取、图纸审查和空间可行性判断。", "二期补充不少于 10 套真实图纸样例及对应人工审查意见。", "甲方/设计单位", "一期不依赖，仅预留上传接口", "不建议纳入一期验收"],
  [14, "BIM资料", "IFC/BIM模型样例与构件语义标准", "P2-二期", "二期", "目前无 BIM/IFC 样例", "缺车站模型、地块模型、接口模型、构件分类、坐标系统、模型精度和审查规则。", "远期 BIM 审查无法落地，只能停留在概念。", "二期明确 IFC 优先还是原生 BIM 优先，并补充样例模型及审查清单。", "甲方/设计单位/模型单位", "一期仅做技术路线预研", "远期难度较高"],
  [15, "可视化输出", "方案图/效果图输出标准", "P2-二期", "二期", "当前有少量 PNG 案例图，但无标准输出要求", "缺图纸深度、表达内容、比例、图例、风格、审查用途、是否可作为正式成果等规定。", "AI出图容易变成演示图，不能用于工程或审查。", "明确意向图、方案图、审查图的边界和交付标准。", "甲方专业组", "一期可输出文字版效果图提示词/表达指引", "作为远期准备"],
  [16, "运维机制", "数据与规则长期维护机制", "P2-二期", "上线运维", "工作方案提到长期维护，但未形成机制表", "缺规范更新响应、数据更新频率、审核流程、版本发布、责任人和留痕机制。", "上线后规则过期或数据失真，影响持续使用。", "建立规则库维护流程和季度/年度复核机制。", "甲方/运营维护方", "可在系统中预留版本号和更新记录", "正式上线前补充"],
];

const confirmations = [
  ["C01", "评分模型", "是否采用样例报告口径作为一期默认口径？", "区位 0.1153、交通 0.3230，并加入出口衔接 0.0254", "P0"],
  ["C02", "赋分尺度", "用地功能是否允许 5 分？", "Excel 表最高 5 分，但样例报告称 1-4 分制", "P0"],
  ["C03", "高效换乘", "一般站赋值是 1 分还是 2 分？", "Excel 为 2 分，样例报告为 1 分", "P0"],
  ["C04", "客流口径", "出行客流使用日均进站量、日均进出站量还是高峰小时量？", "建议一期采用单一口径，并保留备注字段", "P0"],
  ["C05", "等级划分", "是否正式保留“不连地块”？", "样例报告有四档；工作方案部分表述为必连/尽连/可连三档", "P0"],
  ["C06", "站点范围", "一期试点覆盖全线网还是先覆盖部分站点？", "建议先以资料较全的试点站点跑通", "P1"],
  ["C07", "报告格式", "一期报告是否需要导出 Word 正式版？", "建议支持 Word/PDF，Excel用于内部规则和需求管理", "P1"],
  ["C08", "图纸能力", "一期是否排除 CAD/BIM 自动审查？", "建议明确二期范围，避免一期验收扩张", "P1"],
];

const phases = [
  ["一期MVP", "目标", "站点与地块信息录入、必要性评分、联通等级判定、推荐联通方式、生成文字报告。"],
  ["一期MVP", "建议必须补齐", "评分口径、站点基础数据、地块输入字段、客流/出入口/接口数据、结构化规则库、报告模板、测试用例。"],
  ["一期增强", "目标", "特殊场景提示、规则来源追溯、更多场景测试、报告模板精修。"],
  ["二期", "目标", "CAD/总图读取、图纸合规审查、BIM/IFC解析、可视化方案辅助输出。"],
  ["二期", "建议必须补齐", "真实图纸/BIM样例、图层/模型标准、人工审查意见、图纸输出标准。"],
];

function setTitle(sheet, title, subtitle, lastCol) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    fill: palette.dark,
    font: { bold: true, color: palette.white, size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
  sheet.getRange("A1").format.rowHeightPx = 36;
  sheet.getRange(`A2:${lastCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format = {
    fill: palette.lightBlue,
    font: { color: palette.text, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange("A2").format.rowHeightPx = 34;
}

function styleHeader(range) {
  range.format = {
    fill: palette.dark,
    font: { bold: true, color: palette.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
}

function setWidths(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidthPx = width;
  });
}

const summary = workbook.worksheets.add("提报摘要");
setTitle(summary, "互联互通智能体开发资料缺项需求提报表", "基于当前资料包梳理，按一期MVP、一期增强、二期能力分层列出需补充/确认内容。", "H");
summary.getRange("A4:H4").values = [["重要度", "数量", "定位", "处理建议", "", "", "", ""]];
styleHeader(summary.getRange("A4:H4"));
summary.getRange("A5:H7").values = [
  ["P0-必须", gaps.filter((row) => row[3].startsWith("P0")).length, "一期MVP启动前应确认或补齐", "评分口径、站点/地块输入、客流接口数据、结构化规则库", "", "", "", ""],
  ["P1-重要", gaps.filter((row) => row[3].startsWith("P1")).length, "影响一期质量和验收稳定性", "报告模板、测试用例、版本管理、特殊场景、功能边界", "", "", "", ""],
  ["P2-二期", gaps.filter((row) => row[3].startsWith("P2")).length, "不建议纳入一期验收", "CAD/BIM、可视化出图、长期运维机制", "", "", "", ""],
];
summary.getRange("A5:H7").format = { wrapText: true, verticalAlignment: "center" };
summary.getRange("A5:A5").format.fill = palette.red;
summary.getRange("A6:A6").format.fill = palette.amber;
summary.getRange("A7:A7").format.fill = palette.green;
summary.getRange("A9:H9").values = [["总体判断", "", "", "", "", "", "", ""]];
styleHeader(summary.getRange("A9:H9"));
summary.getRange("A10:H12").values = [
  ["当前资料足以支撑一期文字报告版原型，但尚不足以直接作为正式验收规格书。", "", "", "", "", "", "", ""],
  ["一期建议聚焦：输入字段标准化、评分模型、联通方式推荐、报告生成。图纸/BIM审查应明确列为二期。", "", "", "", "", "", "", ""],
  ["开发方可先行完成结构化规则初稿、输入字段模板、报告模板和测试样例；最终评分口径及真实站点数据需甲方确认/补充。", "", "", "", "", "", "", ""],
];
summary.getRange("A10:H12").merge(true);
summary.getRange("A10:H12").format = { wrapText: true, verticalAlignment: "center" };
summary.getRange("A10:H12").format.rowHeightPx = 38;
setWidths(summary, [120, 70, 220, 520, 30, 30, 30, 30]);

const gapSheet = workbook.worksheets.add("缺项清单");
setTitle(gapSheet, "资料缺项清单及重要度分级", "P0=一期必须；P1=重要增强/验收稳定性；P2=二期或上线运维。", "L");
const gapHeaders = ["序号", "缺项类别", "缺项名称", "重要度", "所属阶段", "当前资料状态", "缺失/问题描述", "对智能体影响", "建议补充/确认内容", "建议责任方", "我方可先行处理", "备注"];
gapSheet.getRange("A4:L4").values = [gapHeaders];
styleHeader(gapSheet.getRange("A4:L4"));
gapSheet.getRange(`A5:L${gaps.length + 4}`).values = gaps;
gapSheet.tables.add(`A4:L${gaps.length + 4}`, true, "GapListTable");
gapSheet.getRange(`A5:L${gaps.length + 4}`).format = { wrapText: true, verticalAlignment: "top" };
gapSheet.getRange(`A5:L${gaps.length + 4}`).format.rowHeightPx = 74;
setWidths(gapSheet, [50, 95, 180, 90, 90, 190, 250, 230, 260, 120, 210, 110]);
gapSheet.freezePanes.freezeRows(4);
gapSheet.getRange(`D5:D${gaps.length + 4}`).conditionalFormats.add("containsText", { text: "P0", format: { fill: palette.red, font: { bold: true } } });
gapSheet.getRange(`D5:D${gaps.length + 4}`).conditionalFormats.add("containsText", { text: "P1", format: { fill: palette.amber, font: { bold: true } } });
gapSheet.getRange(`D5:D${gaps.length + 4}`).conditionalFormats.add("containsText", { text: "P2", format: { fill: palette.green, font: { bold: true } } });

const confirmSheet = workbook.worksheets.add("待确认口径");
setTitle(confirmSheet, "需甲方/专业组确认的关键口径", "这些事项不是代码难点，而是专业规则和验收口径，需要在一期开发前或开发初期拍板。", "E");
confirmSheet.getRange("A4:E4").values = [["编号", "类别", "待确认事项", "建议口径/说明", "重要度"]];
styleHeader(confirmSheet.getRange("A4:E4"));
confirmSheet.getRange(`A5:E${confirmations.length + 4}`).values = confirmations;
confirmSheet.tables.add(`A4:E${confirmations.length + 4}`, true, "ConfirmTable");
confirmSheet.getRange(`A5:E${confirmations.length + 4}`).format = { wrapText: true, verticalAlignment: "top" };
confirmSheet.getRange(`A5:E${confirmations.length + 4}`).format.rowHeightPx = 56;
setWidths(confirmSheet, [70, 110, 300, 380, 90]);
confirmSheet.freezePanes.freezeRows(4);

const phaseSheet = workbook.worksheets.add("实施建议");
setTitle(phaseSheet, "建议实施边界与资料补充节奏", "用于需求提报时说明一期、一期增强、二期的边界，避免把图纸/BIM远期能力混入一期验收。", "C");
phaseSheet.getRange("A4:C4").values = [["阶段", "类型", "内容"]];
styleHeader(phaseSheet.getRange("A4:C4"));
phaseSheet.getRange(`A5:C${phases.length + 4}`).values = phases;
phaseSheet.tables.add(`A4:C${phases.length + 4}`, true, "PhaseTable");
phaseSheet.getRange(`A5:C${phases.length + 4}`).format = { wrapText: true, verticalAlignment: "top" };
phaseSheet.getRange(`A5:C${phases.length + 4}`).format.rowHeightPx = 58;
setWidths(phaseSheet, [120, 120, 760]);
phaseSheet.freezePanes.freezeRows(4);

for (const sheet of [summary, gapSheet, confirmSheet, phaseSheet]) {
  const used = sheet.getUsedRange();
  used.format.font = { name: "Microsoft YaHei", size: 10 };
}

const outputPath = `${outputDir}/互联互通智能体资料缺项需求提报表.xlsx`;
const previewPath = `${outputDir}/提报摘要预览.png`;
const inspect = await workbook.inspect({
  kind: "sheet,table",
  maxChars: 4000,
  tableMaxRows: 5,
  tableMaxCols: 6,
});
console.log(inspect.ndjson);

const preview = await workbook.render({ sheetName: "提报摘要", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(JSON.stringify({ outputPath, previewPath }));
