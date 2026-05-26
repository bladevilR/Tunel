# 苏州轨道交通站点周边互联互通智能体

本目录为本地可运行的一期 MVP 交付包。

## 快速启动

```powershell
cd E:\ai\苏州轨道交通站点周边互联互通智能体开发工作提资\outputs\interconnect_agent_system
.\run.ps1
```

打开：

```text
http://127.0.0.1:8765/
```

## 核心功能

- 项目录入
- TOD 站点预设补齐
- 20260507 客流与出入口/接口资料预设补齐
- 标准输入要素表单
- 联通必要性评分
- 按 80/60 百分制阈值判定必连 / 尽连 / 可连
- 联通方式推荐
- 模型主导综合研判，可在保留理由和复核标签的前提下覆盖规则基线结论
- 规则基线 / 模型结论差异说明
- 资料补齐、风险项、证据覆盖和质量标签
- 推荐联通路径示意图 brief
- 客户正式版、专家附录版、领导汇报版三类报告模式
- 规则追溯
- 项目保存、读取、删除
- JSON 评估快照、正式报告与打分明细 Word / PDF 导出
- 实时交付清单 API 与 zip 交付包下载
- 浏览器端到端验收

## 主要入口

- 工作台：`frontend/index.html`
- 后端：`backend/server.py`
- 评分规则：`data/factors.json`
- 方案规则：`data/design_rules.json`
- TOD 站点库：`data/stations.json`
- 客流库：`data/ridership.json`
- 出入口与接口摘要：`data/station_operations.json`
- 运营公司出入口开放与周边配套：`data/station_amenities.json`
- 标准输入字段：`data/input_schema.json`
- 知识数据库：`data/knowledge/`
- 项目库：`data/projects.json`
- 导出目录：`exports/`
- 最新交付清单：`/api/delivery/manifest`
- 最新交付包：`/api/delivery/package`

## 文档

- `docs/delivery_notes.md`：交付说明
- `docs/acceptance_report.md`：验收报告
- `docs/api_reference.md`：API 说明
- `docs/implementation_plan.md`：设计与实现计划
- `docs/feedback_20260507_analysis.md`：20260507反馈提资解析
- `docs/knowledge_database.md`：知识数据库说明
- `docs/function_and_gap_inventory.md`：功能真实化与补齐项梳理
- `docs/delivery_manifest.md`：交付物索引
- `docs/mockups/`：四个理想页面视觉稿
- `docs/product_page_mockup.png`：成品页面视觉稿
- `docs/pilot_input_template.xlsx`：试点录入模板
- `docs/superpowers/specs/2026-05-11-model-led-phase-one-design.md`：模型主导一期设计
- `docs/superpowers/plans/2026-05-11-model-led-phase-one.md`：模型主导一期实施计划

## 验收

```powershell
python -m py_compile .\backend\server.py .\backend\research_agent.py .\tools\verify_model_led_phase_one.py .\tools\verify_model_oriented_research.py
python .\tools\verify_model_led_phase_one.py
python .\tools\verify_model_oriented_research.py
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\verify_system.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_model_led_ui.cjs
```

## 远端部署包

```powershell
python .\tools\build_windows_server_package.py
python .\tools\verify_windows_server_package.py
```

默认生成 `dist/interconnect-agent-server-*-with-key.zip`，包含 `start_server.bat`、内置 Python 运行时和当前 `.env.local`。该包内含模型访问密钥，只用于受控分发。
