# 交付物索引

生成时间：2026-05-08 18:07:52

## 试点必读文件

| 文件 | 大小 | 更新时间 |
|---|---:|---|
| `docs/delivery_notes.md` | 7.4 KB | 2026-05-08 18:06:54 |
| `docs/acceptance_report.md` | 5.7 KB | 2026-05-08 17:04:05 |
| `docs/api_reference.md` | 4.4 KB | 2026-05-08 18:06:42 |
| `docs/function_and_gap_inventory.md` | 4.8 KB | 2026-05-08 17:04:15 |
| `docs/knowledge_database.md` | 7.2 KB | 2026-05-07 15:05:04 |
| `docs/feedback_20260507_analysis.md` | 1.2 KB | 2026-05-07 14:21:09 |
| `docs/llm_integration_contract.md` | 3.2 KB | 2026-05-08 18:07:19 |
| `docs/pilot_input_template.xlsx` | 7.5 KB | 2026-05-07 14:28:55 |

## 界面截图

| 文件 | 大小 | 更新时间 |
|---|---:|---|
| `interconnect_dashboard.png` | 194.4 KB | 2026-05-07 16:59:12 |
| `interconnect_assessment.png` | 276.0 KB | 2026-05-07 16:57:14 |
| `interconnect_knowledge.png` | 583.6 KB | 2026-05-07 16:57:14 |
| `interconnect_reporting.png` | 256.8 KB | 2026-05-07 16:57:14 |
| `interconnect_agent_screenshot.png` | 221.2 KB | 2026-05-08 17:05:16 |

## 理想页面视觉稿

| 文件 | 大小 | 更新时间 |
|---|---:|---|
| `docs/mockups/dashboard-ideal.png` | 1.2 MB | 2026-05-07 16:23:36 |
| `docs/mockups/assessment-ideal.png` | 1.2 MB | 2026-05-07 16:25:46 |
| `docs/mockups/knowledge-ideal.png` | 1.3 MB | 2026-05-07 16:29:40 |
| `docs/mockups/report-completion-ideal.png` | 1.3 MB | 2026-05-07 16:32:40 |

## 最近导出文件

| 文件 | 大小 | 更新时间 |
|---|---:|---|
| `exports/6-JJY-2026-001-20260508-170515.docx` | 41.1 KB | 2026-05-08 17:05:15 |
| `exports/6-JJY-2026-001-20260508-170515-missing.csv` | 26 B | 2026-05-08 17:05:15 |
| `exports/6-JJY-2026-001-20260508-170515-score-detail.csv` | 755 B | 2026-05-08 17:05:15 |
| `exports/6-JJY-2026-001-20260508-170515.json` | 34.9 KB | 2026-05-08 17:05:15 |
| `exports/6-JJY-2026-001-20260508-170515.md` | 11.5 KB | 2026-05-08 17:05:15 |
| `exports/6-JJY-2026-001-20260508-170514.docx` | 41.1 KB | 2026-05-08 17:05:14 |
| `exports/6-JJY-2026-001-20260508-170514-missing.csv` | 26 B | 2026-05-08 17:05:14 |
| `exports/6-JJY-2026-001-20260508-170514-score-detail.csv` | 755 B | 2026-05-08 17:05:14 |
| `exports/6-JJY-2026-001-20260508-170514.json` | 35.0 KB | 2026-05-08 17:05:14 |
| `exports/6-JJY-2026-001-20260508-170514.md` | 11.5 KB | 2026-05-08 17:05:14 |

## 验证入口

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\verify_system.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\tools\seed_station_projects.py
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_station_precheck.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_report_richness.cjs
```
