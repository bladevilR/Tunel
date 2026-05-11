from __future__ import annotations

import argparse
import mimetypes
import os
import json
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
USER_GEOMETRY_PATH = ROOT / "user_geometry.json"
EXPORT_DIR = ROOT / "exports"


class SyncHandler(BaseHTTPRequestHandler):
    server_version = "AmapSyncServer/1.0"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/user-geometry":
            self._serve_user_geometry()
            return

        if path in {"/", "/index.html"}:
            self._serve_html()
            return

        request_path = path.lstrip("/")
        file_path = (ROOT / request_path).resolve()
        if ROOT not in file_path.parents or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self._serve_file(file_path)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/user-geometry":
            self._save_user_geometry()
            return
        if path == "/api/export-png":
            self._export_png()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _serve_html(self) -> None:
        key = os.environ.get("AMAP_JS_KEY", "")
        security_code = os.environ.get("AMAP_SECURITY_CODE", "")
        if not key or not security_code:
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                    if not key:
                        key = winreg.QueryValueEx(env_key, "AMAP_JS_KEY")[0]
                    if not security_code:
                        security_code = winreg.QueryValueEx(env_key, "AMAP_SECURITY_CODE")[0]
            except Exception:
                pass
        html = HTML_PATH.read_text(encoding="utf-8")
        html = html.replace("__AMAP_JS_KEY__", key)
        html = html.replace("__AMAP_SECURITY_CODE__", security_code)
        payload = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, file_path: Path) -> None:
        payload = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_user_geometry(self) -> None:
        if not USER_GEOMETRY_PATH.exists():
            self._send_json(HTTPStatus.OK, {"ok": False, "geometry": None})
            return
        payload = USER_GEOMETRY_PATH.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, status: HTTPStatus, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _save_user_geometry(self) -> None:
        try:
            data = self._read_json_body()
            if not isinstance(data, dict) or "parcel" not in data:
                raise ValueError("geometry payload must include parcel")
            USER_GEOMETRY_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._send_json(HTTPStatus.OK, {"ok": True, "path": str(USER_GEOMETRY_PATH)})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def _export_png(self) -> None:
        try:
            EXPORT_DIR.mkdir(exist_ok=True)
            env = os.environ.copy()
            node_modules = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "node_modules"
            if node_modules.exists() and not env.get("NODE_PATH"):
                env["NODE_PATH"] = str(node_modules)
            completed = subprocess.run(
                ["node", str(ROOT / "export_current_view.cjs")],
                cwd=str(ROOT),
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=70,
            )
            if completed.returncode != 0:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "ok": False,
                        "error": completed.stderr.strip() or completed.stdout.strip(),
                    },
                )
                return
            stdout = completed.stdout or ""
            if not stdout.strip():
                last_export = ROOT / "last_export.json"
                if not last_export.exists():
                    raise RuntimeError("export script returned no JSON")
                stdout = last_export.read_text(encoding="utf-8")
            data = json.loads(stdout)
            self._send_json(HTTPStatus.OK, data)
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve AMap 2D/3D synchronized calibration demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8898)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SyncHandler)
    print(f"http://{args.host}:{args.port}/index.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
