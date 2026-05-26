# 2026-05-25 智能体使用体验反馈处理交付更新

本次更新对应 OpenSpec 变更 `address-agent-experience-feedback`，范围来自《智能体使用体验.docx》中提出的导出、示意图、项目提资、站点复用、报告质量和平台迁移问题。

## 已完成项

- 报告导出改为后端统一生成可下载文件元数据，返回 `filename`、`relativePath`、`downloadUrl`、`contentType`、`size`，前端只使用浏览器可访问链接下载。
- 示意图 PNG 导出返回 `/schematic/exports/...` 下载链接，并修复非默认端口下导出仍访问 `127.0.0.1:8765` 的问题。
- 示意图几何升级为 v2 多对象模型，支持多个地块红线、车站轮廓、通道、出入口和空间对象，并保留旧字段兼容读取。
- 地上楼层上限统一限制为 30；地下空间和建筑空间合并为统一 `spatialItems` 模型。
- 示意图页面新增绘制预览线、对象选择删除、绘图工具栏折叠、3D 俯仰角/旋转角控制与导出视角持久化。
- 项目提资支持版本化 JSON 导入/导出；自定义项目名会参与项目列表、报告标题和导出文件命名。
- 站点搜索改为后端上下文服务，覆盖站点库、客流、运营、配套和知识索引，并支持线路、TOD 层级、日均进站、出入口摘要和站点类型自动填充。
- 正式报告按选定旧版报告的 7 个顶层章节顺序生成，补入客流来源及判断影响、古城保护人工复核项、安全及轨道保护要求提示，并保证 DOCX/PDF 非空输出。
- 平台就绪接口已预留：能力状态、生成图片占位、匿名本地身份、管理员站点轮廓共享数据、管理员轮廓应用到项目几何、服务器迁移说明。

## 仍属于后续 T2/运维深化的项

- 真实账号体系、登录鉴权、多人权限和项目归属迁移尚未启用；当前使用 `data/local_identity.json` 的本地匿名身份。
- 生成图片 API 目前只有稳定占位合同；未配置 `GENERATED_IMAGE_API_ENABLED=1` 和 `OPENAI_API_KEY` 时会返回 `not_configured`，不影响本地示意图 PNG 导出。
- 管理员站点轮廓目前使用 `data/admin_station_outlines.json` 本地共享存储；后续可迁移到数据库和后台维护界面。
- 服务器部署已有 host、port、数据目录、导出目录、运行时依赖和密钥说明，但尚未提供生产级进程守护、反向代理、备份恢复和审计方案。
- 古城保护、轨道保护、安全保护区等仍需要权威图层或人工复核，报告不会在缺少数据时自动给出肯定性结论。

## 验证摘要

- Python 语法检查覆盖 `backend/server.py`、`backend/research_agent.py` 和新增/变更验证脚本。
- Python 验证覆盖站点上下文、平台就绪、PNG 元数据、PNG 子进程错误处理、报告结构质量、客户报告、报告导出合同和导出 HTTP 元数据。
- Node 验证覆盖项目提资/站点上下文合同、站点自动填充合同、示意图工具合同、空间模型、多通道、前端下载元数据、PNG 结果策略、PNG 运行时和报告丰富度。
- Playwright 浏览器验证覆盖站点搜索/自动填充、项目提资导入导出、示意图工具栏桌面及窄屏布局、报告导出、示意图保存和 PNG 导出。

## 关键运行边界

- PNG 导出需要本机或服务器可用的 Chrome/Microsoft Edge，并需要 Node.js 20+ 的 WebSocket 支持。
- 高德地图页面需要 `AMAP_JS_KEY` 和 `AMAP_SECURITY_CODE`；未配置时页面会显示明确失败状态。
- 报告 PDF 优先使用 Word/LibreOffice/PyMuPDF 转换；均不可用时会生成最小 PDF 占位，保证下载合同稳定。
- 需要迁移到服务器时，先阅读 `docs/deployment_server_migration.md`，并备份 `data/`、`exports/`、`frontend/schematic/user_geometry.json`、`frontend/schematic/exports/`。
