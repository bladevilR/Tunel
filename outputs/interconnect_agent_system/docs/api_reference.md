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
- `ridershipForecast`：0528既有线路全日客流预测库，作为未来客流证据，不覆盖现状日均进站。
- `stationMemory`：本地站点记忆库，包含别名、上下文修正和可复用站体轮廓摘要。
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

根据项目输入返回评估结果。请求体可直接传项目 JSON，也可传：

```json
{
  "project": {},
  "researchOptions": {
    "allowOfflineFallback": true,
    "forceOfflineFallback": false
  }
}
```

`allowOfflineFallback` 表示外部模型不可用时允许后端生成本地兜底研判；`forceOfflineFallback` 用于本地验收或演示，强制跳过外部模型调用。

响应核心字段：

- `score`：原始加权分。
- `scorePercent`：折算百分制分值。
- `scoreScale`：折算规则。
- `level`：必连地块 / 尽连地块 / 可连地块。
- `stationContext`：匹配到的客流、出入口接口、运营配套和周边配套。
- `dimensions`：四维评分明细。
- `recommendation`：推荐方案、备选方案和命中规则。
- `researchPlan` / `evidencePack`：模型研判前的研究计划、标杆案例、本地知识库和可用外部检索证据。
- `modelAssessment`：模型或本地兜底生成的动态维度、风险、不确定性和复核问题。
- `modelJudgement`：一期主结论字段。包含 `level`、`recommendedType`、`confidence`、`reason`、`overrideReason`、`riskItems`、`fundingRequests`、`reviewQuestions` 和证据引用。该字段作为展示和报告生成的模型主导结论。
- `modelRuleDifference`：规则基线与模型结论的差异说明。包含 `ruleLevel`、`modelLevel`、`ruleRecommendedType`、`modelRecommendedType`、`status`、`reason` 和 `reviewLabels`；模型可以覆盖规则结论，但必须保留理由与复核标签。
- `modelQuality`：事实诚实、证据覆盖、缺失项数量、证据数量和质量标签。
- `diagramBrief`：推荐联通路径示意图 brief，包含图类型、节点、边、标注和可导出格式。
- `reportModes`：报告模式清单，当前包括客户正式版、专家附录版和领导汇报版。
- `capabilityStatus`：本地知识库、独立搜索、模型调用和兜底状态。
- `clientReport` / `clientReportMode`：客户可读报告章节与生成模式。
- `report`：综合评价报告内容，覆盖评价口径、引用依据、站点研判、维度拆解、方案比选、风险复核、实施建议和模型主导综合研判。
- `llmReviewContext`：供后续接入其他 LLM 或人工专家复核的结构化上下文；包含规则基线、引用依据、四维拆解、方案比选、风险复核点、输出结构约束和模型可覆盖规则结论的边界。
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

根据传入项目数据或 `projectId` 生成交付文件。后端会重新调用 `/api/evaluate` 同一套规则和模型主导研判链路计算评分、等级、推荐方式和报告章节；前端传入的历史 `result` 仅兼容旧调用中的 `result.project`，其中的评分和结论不会被采信。请求体同样支持 `researchOptions`。

- JSON 评估快照，包含 `modelJudgement`、`modelRuleDifference`、`modelQuality`、`diagramBrief`、`reportModes` 和 `llmReviewContext`。该快照为强制产物，会出现在 `files[]` 和 `snapshot` 字段中。
- 正式报告 Word。该 DOCX 为强制产物，生成失败时 `/api/export` 返回显式错误，不返回空下载链接。
- 正式报告 PDF（设置 `INTERCONNECT_EXPORT_PDF=1` 或 `EXPORT_PDF=1` 且本机具备转换能力时生成）。
- 评分明细 Word。
- 评分明细 PDF（设置 PDF 转换开关且可转换时生成）。

响应中的 `files[].relativePath` 可通过 `/exports/...` 下载。

## GET /api/station-memory

返回本地站点记忆记录。可用 `station`、`stationName` 或 `q` 过滤站名/别名。管理员维护的站体轮廓会映射成只读虚拟 memory 记录，便于统一应用。

## POST /api/station-memory

保存站点记忆记录，包含 `identity`、`context`、`schematic`、`notes`、`fieldSources` 和 `provenance`。再次保存同一站点会递增 `version`。

## POST /api/station-memory/apply

将站点记忆显式应用到项目和可选 schematic geometry，并返回 `stationMemorySnapshot`，其中包含 `sourceMemoryId`、`sourceVersion`、`appliedAt` 和 `appliedFields`。未显式应用时，前端自动填充仍会保留用户手动覆盖字段。

## GET /exports/{filename}

下载后端导出的报告文件。

## Platform Readiness APIs

### GET /api/capabilities

Returns explicit capability flags for generated images, accounts, administrator station outlines, and deployment/runtime status. Each item includes at least `enabled` and `mode`.
`deployment.validation` reports resolved host/port, writable data/export paths, generated-image provider consistency, account mode, and optional PDF status.

### GET /api/identity

Returns the local anonymous identity contract by default. When `INTERCONNECT_ACCOUNT_MODE` is enabled, returns a local user owner record while preserving local-first usage.

### POST /api/generated-images

Generated-image endpoint with three structured states:

- disabled: returns `not_configured` and does not affect schematic PNG export.
- local provider: with `GENERATED_IMAGE_PROVIDER=local`, writes a served SVG artifact and metadata under `exports/generated-images/`.
- provider failure: configured providers without an installed adapter return `provider_failure` and do not overwrite existing artifacts.

Successful responses include `image.downloadUrl`, `metadataFile.downloadUrl`, provider metadata, and owner metadata.

### POST /api/ownership/migrate

Migrates a saved anonymous project to the active local account owner. The project id and history are retained, while `owner` and `ownerMigrations[]` record the previous owner and migration timestamp.

### GET /api/admin/station-outlines

Lists shared administrator station outlines from `data/admin_station_outlines.json`. Optional query parameters: `station` or `stationName`.

### POST /api/admin/station-outlines

Saves a shared administrator station outline separately from user project data.

### POST /api/admin/station-outlines/apply

Applies an administrator station outline to a project geometry payload and writes source snapshot metadata, including `kind=admin_station_outline`, `recordId`, `stationName`, and `snapshotAt`.
