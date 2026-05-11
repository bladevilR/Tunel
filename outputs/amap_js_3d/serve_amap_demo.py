from __future__ import annotations

import argparse
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "amap_3d_demo.html"


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "AmapDemoServer/1.0"

    def do_GET(self) -> None:
        if self.path in {"/", "/amap_3d_demo.html"}:
            self._serve_demo()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _serve_demo(self) -> None:
        key = os.environ.get("AMAP_JS_KEY", "")
        security_code = os.environ.get("AMAP_SECURITY_CODE", "")

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the AMap JS 3D demo with local env credentials.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"http://{args.host}:{args.port}/amap_3d_demo.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
