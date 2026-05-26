from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import server  # noqa: E402


def main() -> int:
    missing_output = SimpleNamespace(stdout=None, stderr=None, returncode=1)
    message = server.subprocess_output_text(missing_output, "fallback message")
    if message != "fallback message":
        raise AssertionError(f"unexpected fallback message: {message!r}")

    stdout_only = SimpleNamespace(stdout="  stdout text  ", stderr=None, returncode=1)
    if server.subprocess_output_text(stdout_only, "fallback") != "stdout text":
        raise AssertionError("stdout should be used when stderr is empty")

    source = (ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    export_block = source[source.index("def _export_schematic_png") : source.index("def _static", source.index("def _export_schematic_png"))]
    if 'encoding="utf-8"' not in export_block or 'errors="replace"' not in export_block:
        raise AssertionError("PNG export subprocess must decode stdout/stderr as UTF-8 with replacement")

    print("schematic PNG subprocess handling OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
