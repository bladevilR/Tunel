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

SECRET_ENV_NAMES = [
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "AMAP_JS_KEY",
    "AMAP_SECURITY_CODE",
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


def user_environment_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
            return str(winreg.QueryValueEx(env_key, name)[0]).strip()
    except Exception:
        return ""


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def write_env_local(stage_root: Path, include_key: bool) -> None:
    if not include_key:
        return
    source_values = parse_env_file(ROOT / ".env.local")
    merged = dict(source_values)
    for name in SECRET_ENV_NAMES:
        if not merged.get(name):
            value = user_environment_value(name)
            if value:
                merged[name] = value
    missing = [name for name in SECRET_ENV_NAMES if name in {"LLM_API_KEY", "AMAP_JS_KEY", "AMAP_SECURITY_CODE"} and not merged.get(name)]
    if missing:
        raise FileNotFoundError(f"要求包含密钥，但缺少环境变量: {', '.join(missing)}")
    lines = [f"{name}={merged[name]}" for name in SECRET_ENV_NAMES if merged.get(name)]
    (stage_root / ".env.local").write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    write_env_local(stage_root, include_key)

    (stage_root / "exports").mkdir(exist_ok=True)
    (stage_root / "logs").mkdir(exist_ok=True)

    if with_runtime:
        prepare_embedded_python(stage_root)

    zip_path = DIST_DIR / f"{package_name}.zip"
    write_package(stage_root, zip_path)
    print(f"Package created: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Included .env.local: {'yes' if include_key else 'no'}")
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
