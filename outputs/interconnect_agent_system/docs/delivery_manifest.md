# 交付物索引

生成时间：2026-05-29 14:51:41

## 试点必读文件

| 文件 | 大小 | 更新时间 |
|---|---:|---|
| `docs/delivery_notes.md` | 7.4 KB | 2026-05-08 18:06:54 |
| `docs/acceptance_report.md` | 5.7 KB | 2026-05-08 17:04:05 |
| `docs/api_reference.md` | 7.4 KB | 2026-05-26 17:07:51 |
| `docs/function_and_gap_inventory.md` | 4.8 KB | 2026-05-09 11:20:13 |
| `docs/knowledge_database.md` | 7.2 KB | 2026-05-29 11:27:18 |
| `docs/feedback_20260507_analysis.md` | 1.2 KB | 2026-05-29 11:27:18 |
| `docs/llm_integration_contract.md` | 6.3 KB | 2026-05-11 10:38:26 |
| `docs/pilot_input_template.xlsx` | 7.5 KB | 2026-05-07 14:28:55 |

## 界面截图

| 文件 | 大小 | 更新时间 |
|---|---:|---|

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
| `exports/STATION-阳澄湖中路-20260508-152242.json` | 17.1 KB | 2026-05-29 11:27:18 |
| `exports/STATION-阳澄湖中路-20260508-152242.md` | 3.1 KB | 2026-05-29 11:27:18 |
| `exports/STATION-阳澄湖中路-20260508-152242-missing.csv` | 26 B | 2026-05-29 11:27:18 |
| `exports/STATION-阳澄湖中路-20260508-152242-score-detail.csv` | 759 B | 2026-05-29 11:27:18 |
| `exports/STATION-富翔路-20260509-150437.md` | 20.9 KB | 2026-05-29 11:27:18 |
| `exports/STATION-富翔路-20260509-150437-missing.csv` | 540 B | 2026-05-29 11:27:18 |
| `exports/STATION-富翔路-20260509-150437-score-detail.csv` | 863 B | 2026-05-29 11:27:18 |
| `exports/STATION-富翔路-20260509-150437.json` | 66.6 KB | 2026-05-29 11:27:18 |
| `exports/6-JJY-2026-001-20260525-143047-evaluation-snapshot.json` | 72.1 KB | 2026-05-29 11:27:18 |
| `exports/CORE-BROWSER-IMPORT-20260525-112459-evaluation-snapshot.json` | 74.0 KB | 2026-05-29 11:27:18 |

## 验证入口

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules;C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\verify_system.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\tools\seed_station_projects.py
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_station_precheck.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_report_richness.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_delivery_package.cjs
```
