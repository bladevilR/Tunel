from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import DEMOS, evaluate_project, export_report_file  # noqa: E402


def main() -> int:
    project = DEMOS["cases"][0]
    result = evaluate_project(project, {"useModelReport": False, "useModelResearch": False})
    export = export_report_file(result)
    files = export.get("files") or []
    filenames = sorted(item["filename"] for item in files)

    expected_suffixes = [
        "-formal-report.docx",
        "-formal-report.pdf",
        "-score-detail.docx",
        "-score-detail.pdf",
    ]
    if len(filenames) != len(expected_suffixes):
        raise AssertionError(f"expected 4 exported files, got {len(filenames)}: {filenames}")

    for suffix in expected_suffixes:
        if not any(name.endswith(suffix) for name in filenames):
            raise AssertionError(f"missing export ending with {suffix}: {filenames}")

    forbidden = (".md", ".json", ".csv")
    bad = [name for name in filenames if name.endswith(forbidden)]
    if bad:
        raise AssertionError(f"unexpected machine-readable exports returned: {bad}")

    for item in files:
        path = ROOT / item["relativePath"]
        if not path.exists() or path.stat().st_size <= 0:
            raise AssertionError(f"exported file is missing or empty: {path}")
        if path.suffix.lower() == ".pdf" and path.read_bytes()[:4] != b"%PDF":
            raise AssertionError(f"exported PDF does not have a PDF header: {path}")

    print("export contract OK")
    for name in filenames:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
