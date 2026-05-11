# API Reference

Base URL:

```text
http://127.0.0.1:8765
```

## GET /api/health

健康检查。

## GET /api/bootstrap

返回前端初始化所需数据：

- `factors`：评分因子、权重、等级阈值。
- `rules`：联通方式库与推荐规则。
- `stations`：TOD 站点库。
- `ridership`：2025年月度日均进站客流库。
- `stationOperations`：出入口、联通接口、建设状态和问题摘要。
- `stationAmenities`：运营公司202604出入口开放与周边配套。
- `inputSchema`：标准输入字段。
- `pptRules`：PPT规则摘要。
- `knowledgeCatalog`：知识库统计。
- `sourceManifest`：资料源清单。
- `unparsedSources`：未全文解析、元数据入库和忽略文件清单。
- `exports`：最近导出文件。
- `demos`：示例项目。
- `projects`：已保存项目摘要。

## POST /api/evaluate

根据项目输入返回评估结果。请求体为项目 JSON。

响应核心字段：

- `score`：原始加权分。
- `scorePercent`：折算百分制分值。
- `scoreScale`：折算规则。
- `level`：必连地块 / 尽连地块 / 可连地块。
- `stationContext`：匹配到的客流、出入口接口、运营配套和周边配套。
- `dimensions`：四维评分明细。
- `recommendation`：推荐方案、备选方案和命中规则。
- `report`：不少于 10 章的综合评价报告内容，覆盖评价口径、引用依据、站点研判、维度拆解、方案比选、风险复核、实施建议和 LLM 综合判断框架。
- `llmReviewContext`：供后续接入其他 LLM 或人工专家复核的结构化上下文；包含不可篡改项目事实、引用依据、四维拆解、方案比选、风险复核点、输出结构约束和模型使用边界。
- `missing`：评分字段待补齐项。

## GET /api/projects

返回已保存项目摘要。

## GET /api/projects/{id}

返回单个项目输入和重新计算后的评估结果。

## POST /api/projects

保存项目输入，并同步生成最新评估结果。

## DELETE /api/projects/{id}

删除本地项目库中的项目记录。

## GET /api/knowledge

返回知识数据库摘要：

- `catalog`：来源、知识块、规则卡片、站点索引规模。
- `ruleCards`：规则卡片数量和样例。
- `stationIndex`：站点综合索引覆盖情况。
- `sources`：资料源清单。
- `unparsedSources`：未全文解析、元数据入库和忽略文件清单。

## GET /api/knowledge/search?q={keyword}&limit={n}

对 `data/knowledge/knowledge_chunks.jsonl` 做本地关键词检索，返回匹配片段、来源文件、分类和元数据。用于报告引用、规则追溯和人工查证。

## GET /api/sources

返回资料源清单和补齐项：

- `catalog`：知识库统计。
- `sources`：`source_manifest.json` 内容。
- `unparsedSources`：`unparsed_sources.json` 内容。

## GET /api/exports

从 `exports/` 目录读取真实导出文件，按更新时间倒序返回。前端“最近导出”使用该接口，不写死文件名。

## GET /api/delivery/manifest

实时扫描当前交付目录并返回最新交付清单，不依赖静态写死文件名。响应字段：

- `generatedAt`：清单生成时间。
- `totalFiles` / `totalSize`：纳入交付包的文件数量与总字节数。
- `groups`：按 `runtime`、`docs`、`screenshots`、`mockups`、`exports` 分组的文件清单。
- `files[]`：扁平文件索引，包含 `filename`、`relativePath`、`size`、`updatedAt`。
- `package.downloadUrl`：最新交付 zip 下载地址，当前为 `/api/delivery/package`。

## GET /api/delivery/package

实时生成 zip 交付包，内容与 `/api/delivery/manifest` 的 `files` 一致，并额外包含 `delivery_manifest.json`。响应 `Content-Type` 为 `application/zip`，文件名格式为 `interconnect-agent-delivery-{yyyyMMdd-HHmmss}.zip`。

## POST /api/export

根据传入项目数据或 `projectId` 生成交付文件。后端会重新调用 `/api/evaluate` 同一套规则计算评分、等级、推荐方式和报告章节；前端传入的历史 `result` 仅兼容旧调用中的 `result.project`，其中的评分和结论不会被采信。

- Markdown 报告。
- Word 报告。
- JSON 评估快照。
- JSON 中包含 `llmReviewContext`，可作为外部 LLM 综合判断的事实输入。
- 评分明细 CSV。
- 待补齐清单 CSV。

响应中的 `files[].relativePath` 可通过 `/exports/...` 下载。

## GET /exports/{filename}

下载后端导出的报告文件。
