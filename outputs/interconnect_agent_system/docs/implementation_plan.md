# 互联互通智能体系统实现计划

日期：2026-05-07

## 规则口径

本系统以《互联互通智能体研发工作方案0318.pptx》为一期规则源头。旧示例报告仅用于参考报告章节颗粒度、表达风格和测试案例，不作为规则优先来源。

一期目标对应 PPT 的近期目标：输入车站与周边地块基础信息，输出联通必要性评估报告和联通设计方案建议报告。图纸读取、BIM、AI 审图和工程级平剖面图属于远期能力，本期只预留接口与状态提示。

## 成品页面视觉基准

已生成一张成品工作台页面视觉稿，并归档为 `docs/product_page_mockup.png`，作为本次实现的 UI 对照基准。界面采用专业工程工作台形态，而不是宣传页：

- 左侧导航：项目录入、必要性评估、方案推荐、报告生成、规则库。
- 顶部栏：项目选择、数据完整度、导出操作。
- 主工作区：车站与地块输入、地图/3D 示意预览、评分矩阵、等级判定、推荐方案、报告大纲预览。
- 视觉语言：白/灰底，红线、蓝色通道、紫色站体、白色拟建体块作为工程图层色。

## 技术方案

采用本地前后端分离原型：

- 后端：Python 标准库 HTTP 服务，提供 JSON API，不依赖外部框架。
- 前端：HTML/CSS/JavaScript 单页工作台。
- 数据：JSON 规则库，先基于现有 Excel 和 PPT 预设；后续可由甲方补齐后直接替换。

## 目录结构

```text
outputs/interconnect_agent_system/
  backend/server.py
  data/factors.json
  data/stations.json
  data/design_rules.json
  data/demo_cases.json
  frontend/index.html
  frontend/assets/styles.css
  frontend/assets/app.js
  exports/
  run.ps1
```

## API

- `GET /api/health`：健康检查。
- `GET /api/bootstrap`：一次性返回站点、评分因子、设计规则和示例项目。
- `POST /api/evaluate`：根据项目输入计算评分、等级、推荐方案和报告章节。
- `GET /api/projects`：返回已保存项目库摘要。
- `GET /api/projects/{id}`：读取单个项目及其最近一次评估结果。
- `POST /api/projects`：保存项目输入，同时固化本次评估结果。
- `POST /api/export`：由后端生成 Markdown 报告文件并落到 `exports/`。

## 评估逻辑

评分采用 PPT 的四维框架：

- 功能属性：用地功能、开发强度。
- 区位属性：区位能级。
- 交通属性：出行客流、高效换乘、出口衔接。
- 地下属性：地下空间。

系统预设三档输出：

- `score >= 3.5`：必连地块。
- `3.0 <= score < 3.5`：尽连地块。
- `score < 3.0`：可连地块。

所有缺失字段进入“待补齐”清单，允许先人工覆盖，后续数据补齐后再自动计算。

## 验收点

- 页面能本地访问。
- 示例项目能自动填充并完成评估。
- API 能独立返回评分、等级、推荐方式和报告结构。
- 项目能保存到本地项目库并再次读取。
- 报告能由后端生成 Markdown 文件。
- 页面能显示缺项、依据、推荐方案和报告预览。
- 不把旧示例的“不连地块”作为一期正式等级输出。
