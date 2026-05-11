# 互联互通智能体交付说明

日期：2026-05-07

## 交付范围

本地版“苏州轨道交通站点周边互联互通智能体”已推进为可演示、可试点录入的完整 MVP。系统以《互联互通智能体研发工作方案0318.pptx》为一期规则源，按 20260507 反馈确认“评分口径以评价因子赋值明细表为准”，旧示例报告只作为章节组织和表达方式参考。

## 已实现能力

- 项目录入：参照 `标准输入要素.docx` 扩展所属区划、地块位置、用地面积、功能业态、地下空间说明、规划指标、附件资料等字段。
- 数据预设：内置 240 条 TOD 站点数据、235 条日均进站客流记录、249 条出入口与联通接口站点摘要、235 条运营公司出入口开放与周边配套记录。
- 站点批量预评估：`tools/seed_station_projects.py` 已按 `data/stations.json` 生成 240 个站点级预评估项目，现有站点、客流、出入口、周边配套先入库，具体地块提资不足的字段继续标为待补齐。
- 必要性评估：按功能、区位、交通、地下四维评分，输出原始加权分、百分制分值和“必连 / 尽连 / 可连”三档。
- 等级阈值：按 20260507 反馈暂定 80 分以上必连、60-80 分尽连、60 分以下可连，取消“不连地块”。
- 客流口径：一期优先采用 `每站每月日均进站.xlsx` 的最新月日均进站量，人工输入可覆盖。
- 方案推荐：按联通等级、业态和地下条件推荐地下主通道、地下次通道、风雨连廊等方案。
- 规则追溯：展示等级阈值、当前命中规则、推荐依据、数据是否完整。
- 项目库：支持保存项目、读取已保存项目。
- 报告导出：后端生成 Markdown、Word、JSON 评估快照、待补齐清单 CSV。
- 报告增强：评价报告扩展为不少于 10 章，覆盖评价口径、引用依据、站点研判、周边功能、四维拆解、方案比选、风险约束、资料补齐、实施时序和 LLM 综合判断框架。
- LLM 接入框架：评估结果新增 `llmReviewContext`，为未来接入其他 LLM 提供事实输入、引用依据、维度拆解、方案比选、风险复核点和输出结构约束；模型不得改分、改等级或把缺失资料补成事实。
- 导出重算：`POST /api/export` 只采信项目输入或 `projectId`，导出前由后端重新评分，避免前端历史结果或伪造结论进入交付文件。
- 明细导出：后端生成评分明细 CSV，便于专业人员复核每个因子的原始分、权重和加权分。
- 文件下载：导出文件可通过 `/exports/...` 直接下载。
- 项目管理：支持删除本地保存项目。
- 资料导入：提供 `tools/ingest_feedback_20260507.py`，可复跑生成客流、接口、输入字段和 PPT 摘要数据。
- 知识数据库：提供 `tools/build_knowledge_database.py`，可复跑生成来源清单、知识块、规则卡片、站点综合索引和运营配套数据。
- 前端知识库：工作台内置资料源统计与关键词检索，可直接查询站点、出入口、周边配套、PPT规则和反馈提资切片。
- 前端重构：已按总览工作台、项目评估、知识库、报告与补齐项四个页面重构，移除原静态示意预览，所有页面统计和列表均来自后端或本地数据文件。
- 试点交付状态：总览工作台新增“已完成 / 需外部资料 / 不能自动完成”三栏状态区，补齐项来自当前评估、项目字段和知识库解析缺口，不能自动完成事项明确标注为一期边界而非可点击功能。
- 目标概念图：新增 `docs/mockups/dashboard-concept-20260508.png`，作为当前总览工作台信息层级与视觉对齐基准。
- 导出历史：新增 `/api/exports`，前端最近导出列表读取真实 `exports/` 目录。
- 交付包打包：新增 `/api/delivery/manifest` 和 `/api/delivery/package`，后端实时索引运行入口、交付文档、验收截图、视觉稿和最近导出成果，并按同一清单生成 zip 包。
- 资料源清单：新增 `/api/sources`，前端资料源表和补齐项读取真实知识库清单。
- 补齐项标注：已形成 `docs/function_and_gap_inventory.md`，区分项目字段缺项、知识库解析缺口和无需处理的临时文件。
- 理想页面视觉稿：已生成并归档到 `docs/mockups/`，用于后续继续对齐产品界面。
- 试点模板：提供 `pilot_input_template.xlsx`，字段已同步标准输入要素。
- 验收脚本：浏览器端到端验证页面、保存项目、导出报告、评分矩阵、报告章节、推荐方案和知识库检索。

## 启动方式

```powershell
cd E:\ai\苏州轨道交通站点周边互联互通智能体开发工作提资\outputs\interconnect_agent_system
.\run.ps1
```

默认访问地址：

```text
http://127.0.0.1:8765/
```

## 验收命令

```powershell
python -m py_compile .\backend\server.py .\tools\generate_delivery_assets.py .\tools\ingest_feedback_20260507.py .\tools\build_knowledge_database.py
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\verify_system.cjs
```

最近一次验收结果：

- 页面标题正确。
- 示例项目评分：百分制 62.03 分；原始加权分 2.5306 / 4.0795。
- 联通等级：尽连地块。
- 推荐方式：地下主通道。
- 报告章节：12 章。
- 评分维度：4 维。
- 知识库统计：21 个资料源、1132 条知识块。
- 知识库检索：`金家堰 出入口` 展示 12 条结果。
- 页面错误：0。
- 失败请求：0。
- 导出文件：Markdown、Word、JSON、CSV 均已生成。

## 主要文件

- `backend/server.py`：本地后端服务和规则计算。
- `frontend/index.html`：工作台页面。
- `frontend/assets/app.js`：前端交互与 API 调用。
- `frontend/assets/styles.css`：工作台样式。
- `data/factors.json`：评分因子和等级阈值。
- `data/design_rules.json`：联通方式与推荐规则。
- `data/stations.json`：预设 TOD 站点库。
- `data/ridership.json`：2025年月度日均进站客流库。
- `data/station_operations.json`：出入口、联通接口、建设状态摘要。
- `data/input_schema.json`：标准输入要素字段。
- `data/station_amenities.json`：运营公司202604出入口开放与周边配套。
- `data/knowledge/`：知识数据库目录。
- `data/projects.json`：已保存项目库。
- `exports/`：报告导出目录。
- `verify_system.cjs`：端到端验收脚本。
- `docs/api_reference.md`：本地 API 说明。
- `docs/pilot_input_template.xlsx`：试点录入模板。
- `docs/feedback_20260507_analysis.md`：20260507反馈提资解析。
- `docs/knowledge_database.md`：知识数据库说明。
- `docs/function_and_gap_inventory.md`：功能真实化与补齐项梳理。
- `docs/llm_integration_contract.md`：后续 LLM 综合判断接入契约。
- `docs/delivery_manifest.md`：试点必读文件、截图、视觉稿和最近导出文件索引。
- `/api/delivery/manifest`：运行时生成的最新交付索引。
- `/api/delivery/package`：运行时生成的 zip 交付包下载入口。
- `docs/mockups/`：四个理想页面视觉稿。

## 一期边界

本版本按 PPT 的近期目标交付，聚焦文字评估报告和方案建议报告。CAD/DWG/BIM 读取、施工图审查、工程级平剖面图和三维空间推理属于远期能力，当前仅保留可视辅助和数据接口思路。
