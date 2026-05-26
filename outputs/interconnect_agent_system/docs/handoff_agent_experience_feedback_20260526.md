# 智能体使用体验反馈交接与经验总结

日期：2026-05-26

## 本轮工作结论

本轮围绕《智能体使用体验.docx》完成了一次从问题拆解、OpenSpec 规划、实现、验收、归档到交付文档的完整闭环。OpenSpec 变更 `address-agent-experience-feedback` 已完成 49/49 个任务，并归档到 `openspec/changes/archive/2026-05-25-address-agent-experience-feedback/`。4 个能力规格已同步到主规格目录：

- `openspec/specs/schematic-authoring-export/spec.md`
- `openspec/specs/project-intake-station-context/spec.md`
- `openspec/specs/report-export-content-quality/spec.md`
- `openspec/specs/platform-readiness/spec.md`

## 已落地能力

- 报告导出返回浏览器可下载的文件元数据，覆盖 DOCX/PDF、导出历史和 HTTP 下载合同。
- 示意图 PNG 导出返回 `/schematic/exports/...` 链接，并修复非默认端口下导出仍访问 `127.0.0.1:8765` 的问题。
- 示意图几何升级为 v2 多对象模型，支持多个地块、车站轮廓、通道、出入口和空间对象，同时兼容旧字段。
- 地上楼层上限统一为 30；建筑、地上空间、地下空间合并进统一 `spatialItems` 模型。
- 示意图页面新增绘制预览、对象选择删除、工具栏折叠、3D pitch/rotation 控制和导出视角持久化。
- 项目提资支持版本化 JSON 导入/导出，自定义项目名参与保存、列表、报告标题和导出 slug。
- 站点搜索和上下文自动填充接入站点库、客流、运营、配套和知识索引，支持换乘/普通站类型推断与手动覆盖。
- 正式报告按旧版参考报告的 7 个顶层章节输出，补充客流来源及影响、古城保护人工复核、安全及轨道保护提示。
- 平台就绪接口预留生成图片占位、本地匿名身份、管理员站点轮廓、部署迁移配置和能力状态。

## 验收记录

最近一次人工触发验收覆盖：

- `openspec validate --all`
- `openspec list --json`
- Python 语法检查：`backend/server.py`、`backend/research_agent.py` 和 Python 验证脚本
- Python 合同脚本：站点上下文、平台就绪、PNG 元数据、PNG 子进程、报告质量、客户报告、报告导出、HTTP 下载元数据
- Node 合同脚本：项目提资、站点自动填充、示意图工具、空间模型、多通道、前端下载元数据、PNG 结果策略、PNG 运行时、报告丰富度
- Playwright 端到端脚本：站点搜索/自动填充、项目提资导入导出、示意图工具栏布局、报告下载、草图保存、PNG 导出

验收结果为通过。验收中发现一个真实问题：`verify_schematic_space_model.cjs` 在 OpenSpec 归档后仍读取 active change fixtures，已修复为同时支持 active 和 archived fixture 路径。

## 后续接手注意点

- 当前工作区存在大量验收生成的 `exports/`、`frontend/schematic/exports/` 和 `frontend/schematic/last_export.json` 产物。本次用户明确要求 `commit all`，因此这些产物会随提交进入 PR。
- 当前工作区还有一批旧截图文件删除状态，来源早于最后验收阶段；本次按用户要求提交全部工作区状态，不单独回滚。
- `frontend/schematic/user_geometry.json` 在端到端验收中会被临时覆盖，但 `verify_core_browser_flows.cjs` 已实现备份和恢复，最后复查确认没有留下测试草图 diff。
- PNG 导出依赖本机或服务器可用 Chrome/Microsoft Edge，以及 Node.js 20+ 的 WebSocket 支持。
- 高德地图页面需要 `AMAP_JS_KEY` 和 `AMAP_SECURITY_CODE`；未配置时应显示明确失败状态。
- 生成图片 API 目前是稳定占位合同；未配置 `GENERATED_IMAGE_API_ENABLED=1` 和 `OPENAI_API_KEY` 时返回 `not_configured`。
- 管理员站点轮廓当前使用 `data/admin_station_outlines.json` 本地 JSON 存储，后续可迁移为数据库和后台维护界面。

## 建议的后续工程化

- 把目前散落的验收脚本收敛为一个 `tools/run_acceptance.py`，支持 `smoke`、`full`、`handoff` 三档。
- 验收产物建议输出到 `acceptance_runs/YYYYMMDD-HHMMSS/`，包含摘要 JSON、Markdown 报告、日志、截图和生成文件索引。
- 后续 PR 前优先运行 `handoff` 档，避免归档、端口、下载链接、浏览器运行时等问题回归。
