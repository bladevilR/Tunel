from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"


def latest_package() -> Path | None:
    packages = sorted(DIST_DIR.glob("interconnect-agent-server-*.zip"), key=lambda item: item.stat().st_mtime)
    return packages[-1] if packages else None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def assert_required_files(package_root: Path) -> None:
    required = [
        "start_server.bat",
        "README_DEPLOY.md",
        "requirements-server.txt",
        ".env.local",
        ".env.example",
        "backend/server.py",
        "backend/research_agent.py",
        "frontend/index.html",
        "frontend/assets/app.js",
        "data/factors.json",
        "data/design_rules.json",
        "data/demo_cases.json",
        "data/knowledge/knowledge_chunks.jsonl",
        "docs/api_reference.md",
    ]
    missing = [item for item in required if not (package_root / item).exists()]
    if missing:
        raise AssertionError(f"部署包缺少必要文件: {missing}")

    forbidden = [
        "server.out.log",
        "server.err.log",
        "model_led_ui_verify.json",
        "model_led_ui_verify.png",
    ]
    leaked = [item for item in forbidden if (package_root / item).exists()]
    if leaked:
        raise AssertionError(f"部署包包含不应分发的本地文件: {leaked}")

    env_local = (package_root / ".env.local").read_text(encoding="utf-8", errors="replace")
    required_env = ["LLM_API_KEY=", "AMAP_JS_KEY=", "AMAP_SECURITY_CODE="]
    missing_env = [name for name in required_env if name not in env_local]
    if missing_env:
        raise AssertionError(f".env.local 缺少必要密钥配置: {missing_env}")


def wait_for_health(port: int, proc: subprocess.Popen[str]) -> dict:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + 35
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            output = ""
            if proc.stdout:
                output = proc.stdout.read()[-4000:]
            raise AssertionError(f"启动脚本提前退出，退出码 {proc.returncode}。\n{output}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(0.5)
    raise AssertionError(f"等待健康检查超时: {last_error}")


def read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def read_compressed(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return response.read(), response.headers.get("Content-Encoding", "")


def read_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=8) as response:
        return response.read().decode("utf-8", errors="replace")


def verify_package(zip_path: Path) -> dict:
    if not zip_path.exists():
        raise FileNotFoundError(f"找不到部署包: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise AssertionError(f"不是有效 zip 文件: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="interconnect-package-") as temp_dir:
        extract_dir = Path(temp_dir)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        roots = [item for item in extract_dir.iterdir() if item.is_dir()]
        if len(roots) != 1:
            raise AssertionError(f"zip 顶层应只有一个目录，实际为: {[item.name for item in roots]}")
        package_root = roots[0]
        assert_required_files(package_root)

        port = free_port()
        env = {
            **os.environ,
            "INTERCONNECT_HOST": "127.0.0.1",
            "INTERCONNECT_PORT": str(port),
            "INTERCONNECT_SKIP_BROWSER": "1",
            "INTERCONNECT_NO_PAUSE": "1",
            "INTERCONNECT_SKIP_SETUP": "1",
            "PYTHONUTF8": "1",
        }
        proc = subprocess.Popen(
            ["cmd.exe", "/c", "start_server.bat"],
            cwd=package_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            health = wait_for_health(port, proc)
            home = read_text(f"http://127.0.0.1:{port}/")
            schematic = read_text(f"http://127.0.0.1:{port}/schematic/index.html")
            bootstrap = read_json(f"http://127.0.0.1:{port}/api/bootstrap")
            compressed_bootstrap, content_encoding = read_compressed(f"http://127.0.0.1:{port}/api/bootstrap")
            if "苏州轨道交通站点周边互联互通智能体" not in home:
                raise AssertionError("首页 HTML 未包含应用标题")
            if "__AMAP_JS_KEY__" in schematic or "__AMAP_SECURITY_CODE__" in schematic:
                raise AssertionError("高德 Key 未注入 schematic 页面")
            demos = (bootstrap.get("demos") or {}).get("cases") or []
            factors = (bootstrap.get("factors") or {}).get("dimensions") or []
            if not demos or not factors:
                raise AssertionError("bootstrap 数据不完整")
            if content_encoding != "gzip" or len(compressed_bootstrap) > 450_000:
                raise AssertionError(f"bootstrap 压缩异常: encoding={content_encoding}, bytes={len(compressed_bootstrap)}")
        finally:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, text=True)

    return {
        "ok": True,
        "zip": str(zip_path),
        "size": zip_path.stat().st_size,
        "health": health,
        "bootstrap": {
            "demos": len(demos),
            "dimensions": len(factors),
            "compressedBytes": len(compressed_bootstrap),
            "contentEncoding": content_encoding,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="验证远端 Windows 服务端部署 zip。")
    parser.add_argument("zip", nargs="?", help="部署 zip 路径；默认取 dist 下最新包。")
    args = parser.parse_args()

    zip_path = Path(args.zip).resolve() if args.zip else latest_package()
    if not zip_path:
        raise FileNotFoundError("dist 下没有 interconnect-agent-server-*.zip")
    result = verify_package(zip_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
