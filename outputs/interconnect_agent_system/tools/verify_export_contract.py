from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import DEMOS, evaluate_project, export_report_file  # noqa: E402


def assert_download_metadata(item: dict) -> None:
    required = {"filename", "relativePath", "downloadUrl", "contentType", "size"}
    missing = sorted(required - set(item))
    if missing:
        raise AssertionError(f"missing download metadata fields {missing} for {item}")
    if not item["downloadUrl"].startswith("/exports/"):
        raise AssertionError(f"downloadUrl should use served /exports/ route: {item}")
    if "\\" in item["relativePath"]:
        raise AssertionError(f"relativePath should be URL-safe/as_posix style: {item}")
    if item["size"] <= 0:
        raise AssertionError(f"exported file should have a positive size: {item}")
    if not item["contentType"]:
        raise AssertionError(f"contentType should be populated: {item}")


def main() -> int:
    project = DEMOS["cases"][0]
    result = evaluate_project(project, {"useModelReport": False, "useModelResearch": False})
    export = export_report_file(result)
    files = export.get("files") or []
    filenames = sorted(item["filename"] for item in files)

    expected_suffixes = [
        "-formal-report.docx",
        "-evaluation-snapshot.json",
        "-score-detail.docx",
    ]
    for suffix in expected_suffixes:
        if not any(name.endswith(suffix) for name in filenames):
            raise AssertionError(f"missing export ending with {suffix}: {filenames}")

    forbidden = (".md", ".csv")
    bad = [name for name in filenames if name.endswith(forbidden)]
    if bad:
        raise AssertionError(f"unexpected machine-readable exports returned: {bad}")

    assert_download_metadata(export)
    assert_download_metadata(export.get("snapshot") or {})
    for item in files:
        assert_download_metadata(item)
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
