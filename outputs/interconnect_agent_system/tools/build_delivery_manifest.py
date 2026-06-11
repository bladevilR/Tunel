from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXPORTS = ROOT / "exports"
TARGET = DOCS / "delivery_manifest.md"


def human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def file_row(path: Path) -> str:
    stat = path.stat()
    updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    rel = path.relative_to(ROOT).as_posix()
    return f"| `{rel}` | {human_size(stat.st_size)} | {updated} |"


def latest_exports(limit: int = 10) -> list[Path]:
    if not EXPORTS.exists():
        return []
    files = [path for path in EXPORTS.iterdir() if path.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return files[:limit]


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    required_docs = [
        "delivery_notes.md",
        "acceptance_report.md",
        "api_reference.md",
        "function_and_gap_inventory.md",
        "knowledge_database.md",
        "feedback_20260507_analysis.md",
        "llm_integration_contract.md",
        "pilot_input_template.xlsx",
    ]
    screenshots = [
        "interconnect_dashboard.png",
        "interconnect_assessment.png",
        "interconnect_knowledge.png",
        "interconnect_reporting.png",
        "interconnect_agent_screenshot.png",
    ]
    mockups = [
        "docs/mockups/dashboard-ideal.png",
        "docs/mockups/assessment-ideal.png",
        "docs/mockups/knowledge-ideal.png",
        "docs/mockups/report-completion-ideal.png",
    ]

    lines = [
        "# 交付物索引",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 试点必读文件",
        "",
        "| 文件 | 大小 | 更新时间 |",
        "|---|---:|---|",
    ]
    for name in required_docs:
        path = DOCS / name
        if path.exists():
            lines.append(file_row(path))

    lines.extend([
        "",
        "## 界面截图",
        "",
        "| 文件 | 大小 | 更新时间 |",
        "|---|---:|---|",
    ])
    for name in screenshots:
        path = ROOT / name
        if path.exists():
            lines.append(file_row(path))

    lines.extend([
        "",
        "## 理想页面视觉稿",
        "",
        "| 文件 | 大小 | 更新时间 |",
        "|---|---:|---|",
    ])
    for rel in mockups:
        path = ROOT / rel
        if path.exists():
            lines.append(file_row(path))

    lines.extend([
        "",
        "## 最近导出文件",
        "",
        "| 文件 | 大小 | 更新时间 |",
        "|---|---:|---|",
    ])
    for path in latest_exports():
        lines.append(file_row(path))

    lines.extend([
        "",
        "## 验证入口",
        "",
        "```powershell",
        "$env:NODE_PATH='C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\.pnpm\\node_modules;C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules'",
        "& 'C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' .\\verify_system.cjs",
        "& 'C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe' .\\tools\\seed_station_projects.py",
        "& 'C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' .\\tools\\verify_station_precheck.cjs",
        "& 'C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' .\\tools\\verify_report_richness.cjs",
        "& 'C:\\Users\\R\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' .\\tools\\verify_delivery_package.cjs",
        "```",
        "",
    ])
    with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    print(TARGET.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
