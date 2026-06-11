from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "backend" / "server.py"


def load_server():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))
    spec = importlib.util.spec_from_file_location("interconnect_server_platform_paths", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str, detail=None) -> None:
    if not condition:
        raise AssertionError(json.dumps({"message": message, "detail": detail}, ensure_ascii=False, indent=2))


def backup(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def restore(path: Path, content: str | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
    else:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    server = load_server()
    original_env = {key: os.environ.get(key) for key in [
        "GENERATED_IMAGE_PROVIDER",
        "GENERATED_IMAGE_API_ENABLED",
        "INTERCONNECT_ACCOUNT_MODE",
        "INTERCONNECT_ACCOUNT_ID",
        "INTERCONNECT_ACCOUNT_NAME",
        "INTERCONNECT_SECRET_KEY",
    ]}
    project_backup = backup(server.PROJECTS_PATH)
    identity_backup = backup(server.LOCAL_IDENTITY_PATH)
    memory_backup = backup(server.STATION_MEMORY_PATH)
    generated_files: list[Path] = []
    try:
        os.environ["GENERATED_IMAGE_PROVIDER"] = "local"
        os.environ["GENERATED_IMAGE_API_ENABLED"] = "1"
        image = server.generated_image_response({"prompt": "platform integration station image", "stationName": "平台测试站"})
        require(image.get("ok") is True, "local generated-image provider should create an artifact", image)
        image_path = ROOT / image["image"]["relativePath"]
        metadata_path = ROOT / image["metadataFile"]["relativePath"]
        generated_files.extend([image_path, metadata_path])
        require(image_path.exists() and image_path.stat().st_size > 0, "generated image artifact should exist", image)
        require(image["image"]["downloadUrl"].startswith("/exports/generated-images/"), "generated image should use served export URL", image)
        require((image.get("metadata") or {}).get("owner", {}).get("ownerId"), "generated image metadata should include owner", image)

        os.environ["INTERCONNECT_ACCOUNT_MODE"] = "local_account"
        os.environ["INTERCONNECT_ACCOUNT_ID"] = "local-user-platform-test"
        os.environ["INTERCONNECT_ACCOUNT_NAME"] = "Platform Test User"
        identity = server.local_identity_payload()
        require(identity["identity"]["type"] == "local_user", "account mode should return local user identity", identity)

        saved = server.save_project_record({
            "id": "platform-owner-project",
            "name": "Platform Owner Project",
            "station": {"name": "平台测试站"},
            "parcel": {},
        }, {"skipEvaluation": True})
        require(saved["owner"]["ownerId"] == "local-user-platform-test", "saved project should include owner metadata", saved)

        migrated = server.migrate_project_owner("platform-owner-project", {
            "ownerId": "local-user-platform-target",
            "ownerType": "local_user",
            "accountMode": "local_account",
            "scope": "local_account",
            "action": "ownership_migration",
            "recordedAt": server.utc_now(),
        })
        require(migrated["id"] == "platform-owner-project", "ownership migration should keep stable project id", migrated)
        require(migrated["owner"]["ownerId"] == "local-user-platform-target", "ownership migration should set target owner", migrated)
        require(migrated.get("ownerMigrations"), "ownership migration should record migration history", migrated)

        memory = server.save_station_memory_record({
            "stationName": "平台测试站",
            "project": {"station": {"name": "平台测试站", "line": "6"}},
        })
        require(memory.get("owner", {}).get("ownerType") == "local_user", "station memory should include owner metadata", memory)

        validation = server.validate_server_configuration()
        require(validation["ok"] is True, "deployment validation should pass with local provider", validation)

        print(json.dumps({
            "ok": True,
            "image": image["image"]["downloadUrl"],
            "owner": saved["owner"]["ownerId"],
            "migratedOwner": migrated["owner"]["ownerId"],
            "validation": validation["resolved"],
        }, ensure_ascii=False, indent=2))
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        restore(server.PROJECTS_PATH, project_backup)
        restore(server.LOCAL_IDENTITY_PATH, identity_backup)
        restore(server.STATION_MEMORY_PATH, memory_backup)
        for path in generated_files:
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    main()
