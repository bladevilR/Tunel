from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description="检查首屏 bootstrap 响应是否启用压缩并控制体积。")
    parser.add_argument("--url", default="http://127.0.0.1:8765/api/bootstrap")
    parser.add_argument("--max-compressed-bytes", type=int, default=450_000)
    parser.add_argument("--max-ms", type=int, default=2500)
    args = parser.parse_args()

    request = urllib.request.Request(args.url, headers={"Accept-Encoding": "gzip"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        headers = dict(response.headers.items())
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    result = {
        "ok": (
            headers.get("Content-Encoding") == "gzip"
            and len(body) <= args.max_compressed_bytes
            and elapsed_ms <= args.max_ms
        ),
        "url": args.url,
        "elapsedMs": elapsed_ms,
        "bytes": len(body),
        "contentEncoding": headers.get("Content-Encoding", ""),
        "contentType": headers.get("Content-Type", ""),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
