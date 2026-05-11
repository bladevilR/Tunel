from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "data" / "knowledge"
LEGACY_DOC_NAME = "轨道站点出入口周边空间一体化设计指引(1).doc"
CONVERTED_DOCX_NAME = "轨道站点出入口周边空间一体化设计指引(1).docx"


def load_json(name: str):
    return json.loads((KNOWLEDGE_DIR / name).read_text(encoding="utf-8"))


def main() -> int:
    unparsed = load_json("unparsed_sources.json")
    legacy_unparsed = [
        item
        for item in unparsed
        if item.get("path", "").endswith(LEGACY_DOC_NAME)
        and item.get("parseStatus") == "unparsed"
    ]
    if legacy_unparsed:
        raise SystemExit(f"legacy Word document is still unparsed: {legacy_unparsed[0]}")

    manifest = load_json("source_manifest.json")
    legacy_entries = [
        item for item in manifest if item.get("path", "").endswith(LEGACY_DOC_NAME)
    ]
    if not legacy_entries:
        raise SystemExit("legacy Word document is missing from source manifest")
    if legacy_entries[0].get("parseStatus") != "parsed":
        raise SystemExit(f"legacy Word manifest entry is not parsed: {legacy_entries[0]}")

    chunks_path = KNOWLEDGE_DIR / "knowledge_chunks.jsonl"
    converted_chunks = 0
    with chunks_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if item.get("sourceName") == CONVERTED_DOCX_NAME:
                converted_chunks += 1

    if converted_chunks < 10:
        raise SystemExit(
            f"converted DOCX yielded too few knowledge chunks: {converted_chunks}"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "legacyDocStatus": legacy_entries[0].get("parseStatus"),
                "convertedDocxChunks": converted_chunks,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
