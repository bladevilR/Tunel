from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import server  # noqa: E402


def main() -> int:
    export_dir = server.SCHEMATIC_EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    png_path = export_dir / "metadata-contract-test.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\nmetadata")

    try:
        result = {
            "ok": True,
            "outputPath": str(png_path),
            "automation": "contract-test",
            "pageErrors": [],
            "pageWarnings": [],
            "failedRequests": [],
        }
        enriched = server.schematic_png_export_response(result)
        export = enriched.get("export") or {}

        if enriched.get("downloadUrl") != "/schematic/exports/metadata-contract-test.png":
            raise AssertionError(f"unexpected top-level downloadUrl: {enriched}")
        if export.get("downloadUrl") != enriched.get("downloadUrl"):
            raise AssertionError(f"nested export should carry same downloadUrl: {enriched}")
        if export.get("relativePath") != "schematic/exports/metadata-contract-test.png":
            raise AssertionError(f"unexpected relativePath: {enriched}")
        if export.get("contentType") != "image/png":
            raise AssertionError(f"unexpected contentType: {enriched}")
        if export.get("size", 0) <= 0:
            raise AssertionError(f"missing positive size: {enriched}")
    finally:
        png_path.unlink(missing_ok=True)

    print("schematic PNG export metadata OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
