from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import DEMOS, evaluate_project, export_report_file  # noqa: E402


EXPECTED_TITLES = [
    "项目概况",
    "联通必要性评估结论",
    "联通方式比选与推荐方案",
    "方案设计核心技术要求",
    "合规性校验说明",
    "设计优化与实施建议",
    "意向效果图输出指引",
]

REQUIRED_TERMS = [
    "客流",
    "每站每月日均进站.xlsx",
    "判断影响",
    "古城保护",
    "历史文化",
    "人工复核",
    "轨道交通保护区",
    "安全保护区",
    "消防",
    "疏散",
]


def fail(message: str, detail=None) -> None:
    raise AssertionError(json.dumps({"message": message, "detail": detail}, ensure_ascii=False, indent=2))


def docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "", xml)
    return text


def docx_xml(path: Path) -> str:
    with ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def main() -> None:
    project = next(item for item in DEMOS["cases"] if item["id"] == "jinjiayan-neighborhood-center")
    result = evaluate_project(project, {"allowOfflineFallback": True, "forceOfflineFallback": True})
    sections = result.get("clientReport") or []
    titles = [item.get("title") for item in sections]
    if titles != EXPECTED_TITLES:
        fail("client report should follow the selected legacy report section order", titles)
    for section in sections:
        if len(section.get("content") or "") < 180:
            fail("report section content is too thin", section)

    text = "\n".join(f"{item.get('title')}\n{item.get('content')}" for item in sections)
    for term in REQUIRED_TERMS:
        if term not in text:
            fail(f"report is missing required wording: {term}", text[:1800])

    export = export_report_file(result)
    files = export.get("files") or []
    formal_docx = next((Path(item["path"]) for item in files if item["filename"].endswith("-formal-report.docx")), None)
    formal_pdf = next((Path(item["path"]) for item in files if item["filename"].endswith("-formal-report.pdf")), None)
    snapshot = export.get("snapshot") or {}
    if not formal_docx or formal_docx.stat().st_size <= 0:
        fail("formal DOCX should be exported and non-empty", files)
    if not snapshot.get("filename", "").endswith("-evaluation-snapshot.json"):
        fail("evaluation snapshot should be exported as mandatory evidence", export)
    if not Path(snapshot.get("path", "")).exists() or Path(snapshot.get("path", "")).stat().st_size <= 0:
        fail("evaluation snapshot should be non-empty", snapshot)
    if formal_pdf and formal_pdf.stat().st_size <= 0:
        fail("formal PDF should be non-empty when generated", files)

    exported_text = docx_text(formal_docx)
    for title in EXPECTED_TITLES:
        if title not in exported_text:
            fail(f"exported DOCX is missing section title: {title}", formal_docx)
    for term in ["评分总览", "推荐方案与备选方案", "资料补齐"]:
        if term not in exported_text:
            fail(f"exported DOCX is missing required structural block: {term}", formal_docx)
    xml = docx_xml(formal_docx)
    if xml.count("<w:tbl") < 3:
        fail("exported DOCX should include summary, dimension, and recommendation/evidence tables", formal_docx)

    print(json.dumps({
        "ok": True,
        "sectionCount": len(sections),
        "docx": str(formal_docx),
        "pdf": str(formal_pdf) if formal_pdf else None,
        "snapshot": snapshot.get("filename"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
