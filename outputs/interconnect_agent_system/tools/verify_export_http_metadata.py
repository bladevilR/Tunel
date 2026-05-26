from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import DEMOS  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int, process: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(f"server exited early\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/bootstrap", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise AssertionError("server did not become ready")


def http_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        with urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def assert_file_metadata(item: dict) -> None:
    for key in ("filename", "relativePath", "downloadUrl", "contentType", "size"):
        if key not in item:
            raise AssertionError(f"missing {key}: {item}")
    if not item["downloadUrl"].startswith("/exports/"):
        raise AssertionError(f"downloadUrl should point at /exports/: {item}")
    if item["size"] <= 0:
        raise AssertionError(f"size should be positive: {item}")


def main() -> int:
    port = free_port()
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        wait_for_server(port, process)
        base = f"http://127.0.0.1:{port}"
        export_response = http_json(
            f"{base}/api/export",
            {
                "project": DEMOS["cases"][0],
                "researchOptions": {"useModelReport": False, "useModelResearch": False},
            },
        )
        if not export_response.get("ok"):
            raise AssertionError(f"export failed: {export_response}")
        files = export_response.get("export", {}).get("files") or []
        if not files:
            raise AssertionError(f"export returned no files: {export_response}")
        for item in files:
            assert_file_metadata(item)

        history_response = http_json(f"{base}/api/exports")
        history = history_response.get("exports") or []
        history_names = {item.get("filename") for item in history}
        for item in files:
            if item["filename"] not in history_names:
                raise AssertionError(f"{item['filename']} missing from /api/exports history")
        for item in history[: len(files)]:
            assert_file_metadata(item)
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)

    print("export HTTP metadata OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
