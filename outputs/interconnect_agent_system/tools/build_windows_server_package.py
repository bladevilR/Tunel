from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
CACHE_DIR = DIST_DIR / ".cache"
PYTHON_VERSION = "3.13.2"
PYTHON_EMBED_NAME = f"python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{PYTHON_EMBED_NAME}"


PACKAGE_DIRS = [
    "backend",
    "data",
    "docs",
    "frontend",
]

PACKAGE_FILES = [
    ".env.example",
    "README.md",
    "requirements-server.txt",
    "run.ps1",
    "verify_system.cjs",
]

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "dist",
    "exports",
    "logs",
    "node_modules",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def copy_tree(src: Path, dst: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            path = Path(name)
            if name in EXCLUDE_DIR_NAMES or path.suffix.lower() in EXCLUDE_SUFFIXES:
                ignored.add(name)
            if name in {"server.out.log", "server.err.log", "model_led_ui_verify.json", "model_led_ui_verify.png"}:
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, ignore=ignore)


def download_python_embed() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / PYTHON_EMBED_NAME
    if target.exists() and target.stat().st_size > 5_000_000:
        return target
    print(f"Downloading Python embedded runtime: {PYTHON_EMBED_URL}")
    urllib.request.urlretrieve(PYTHON_EMBED_URL, target)
    return target


def prepare_embedded_python(stage_root: Path) -> None:
    runtime_dir = stage_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    embed_zip = download_python_embed()
    with zipfile.ZipFile(embed_zip) as archive:
        archive.extractall(runtime_dir)

    pth_files = list(runtime_dir.glob("python*._pth"))
    if pth_files:
        pth_file = pth_files[0]
        lines = [
            line.strip()
            for line in pth_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and line.strip() != "#import site"
        ]
        for entry in ["..\\..", "..\\..\\backend", "Lib\\site-packages"]:
            if entry not in lines:
                lines.append(entry)
        if "import site" not in lines:
            lines.append("import site")
        pth_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    site_packages = runtime_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    requirements = ROOT / "requirements-server.txt"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--no-cache-dir",
            "--only-binary=:all:",
            "--target",
            str(site_packages),
            "-r",
            str(requirements),
        ],
        check=True,
    )

    subprocess.run(
        [
            str(runtime_dir / "python.exe"),
            "-c",
            "import docx, fitz; print('embedded runtime ok')",
        ],
        check=True,
    )

    for cache_dir in runtime_dir.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)


def write_package(stage_root: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in sorted(stage_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(stage_root.parent))


def build_package(include_key: bool = True, with_runtime: bool = True) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    package_name = f"interconnect-agent-server-{stamp}{'-with-key' if include_key else ''}"
    stage_root = DIST_DIR / "staging" / package_name
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)

    for dirname in PACKAGE_DIRS:
        copy_tree(ROOT / dirname, stage_root / dirname)

    for filename in PACKAGE_FILES:
        src = ROOT / filename
        if src.exists():
            shutil.copy2(src, stage_root / filename)

    shutil.copy2(ROOT / "deploy" / "start_server.bat", stage_root / "start_server.bat")
    shutil.copy2(ROOT / "deploy" / "README_DEPLOY.md", stage_root / "README_DEPLOY.md")

    env_local = ROOT / ".env.local"
    if include_key and env_local.exists():
        shutil.copy2(env_local, stage_root / ".env.local")
    elif include_key:
        raise FileNotFoundError("要求包含密钥，但项目根目录没有 .env.local")

    (stage_root / "exports").mkdir(exist_ok=True)
    (stage_root / "logs").mkdir(exist_ok=True)

    if with_runtime:
        prepare_embedded_python(stage_root)

    zip_path = DIST_DIR / f"{package_name}.zip"
    write_package(stage_root, zip_path)
    print(f"Package created: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Included .env.local: {'yes' if include_key and env_local.exists() else 'no'}")
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 Windows 远端部署服务端 zip。")
    parser.add_argument("--without-key", action="store_true", help="不把 .env.local 放进部署包。")
    parser.add_argument("--without-runtime", action="store_true", help="不打包嵌入式 Python 运行时。")
    args = parser.parse_args()
    build_package(include_key=not args.without_key, with_runtime=not args.without_runtime)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Build failed: {exc}", file=sys.stderr)
        raise
