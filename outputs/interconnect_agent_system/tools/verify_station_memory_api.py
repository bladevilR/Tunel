from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "backend" / "server.py"


def load_server():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))
    spec = importlib.util.spec_from_file_location("interconnect_server_memory", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    server = load_server()
    memory_path = server.STATION_MEMORY_PATH
    original = memory_path.read_text(encoding="utf-8") if memory_path.exists() else None
    try:
        payload = {
            "stationName": "站点记忆测试站",
            "identity": {
                "canonicalName": "站点记忆测试站",
                "displayName": "站点记忆测试站",
                "aliases": ["记忆别名站"],
            },
            "project": {
                "id": "memory-test-project",
                "station": {
                    "name": "站点记忆测试站",
                    "line": "6",
                    "todLevel": "T2",
                    "locationLevel": "city",
                    "stationType": "planned_transfer",
                    "district": "测试区",
                    "dailyInbound": 6789,
                    "nearbyExit": "9号口",
                    "interfaceCondition": "记忆中的接口条件",
                },
            },
            "schematic": {
                "stationOutlines": [{
                    "id": "memory-outline-test",
                    "name": "测试站体",
                    "path": [[120.1, 31.1], [120.2, 31.1], [120.2, 31.2], [120.1, 31.2]],
                }],
            },
            "sourceLabels": ["verification"],
        }
        record_v1 = server.save_station_memory_record(payload)
        require(record_v1["version"] == 1, "new memory record should start at version 1")
        require(record_v1["context"]["stationType"] == "planned_transfer", "station type should be stored")

        alias_context = server.station_context_payload("记忆别名站")
        require(alias_context["memory"]["id"] == record_v1["id"], "alias search should find memory record")
        require(alias_context["suggestedFields"]["station.stationType"] == "planned_transfer", "memory should prefill station type")
        require(any(item["key"] == "memory" for item in alias_context["sources"]), "context should label memory source")

        manual_context = server.station_context_payload("记忆别名站", {"stationType": "normal", "line": "8"})
        require(manual_context["suggestedFields"]["station.stationType"] == "normal", "manual station type override should be preserved")
        require(manual_context["suggestedFields"]["station.line"] == "8", "manual line override should be preserved")

        applied = server.apply_station_memory_payload({
            "stationName": "记忆别名站",
            "project": {"station": {"name": "记忆别名站", "stationType": "normal"}},
            "geometry": {"stationOutlines": []},
            "force": True,
        })
        snapshot = applied["project"].get("stationMemorySnapshot") or {}
        require(snapshot.get("sourceMemoryId") == record_v1["id"], "applied project should store memory id")
        require(snapshot.get("sourceVersion") == 1, "applied project should snapshot memory version")
        require(applied["project"]["station"]["stationType"] == "planned_transfer", "explicit apply should use memory station type")
        require(applied["geometry"].get("stationOutlines"), "apply should reuse memory station outline")

        preserved = server.apply_station_memory_to_project(
            {"station": {"name": "记忆别名站", "stationType": "normal"}},
            record_v1,
            force=False,
        )
        require(preserved["station"]["stationType"] == "normal", "non-forced apply should preserve manual fields")

        record_v2 = server.save_station_memory_record({**payload, "context": {"stationType": "current_transfer"}})
        require(record_v2["version"] == 2, "saving same memory should increment version")
        require(snapshot.get("sourceVersion") == 1, "existing project snapshot should remain immutable after memory edit")

        admin_records = server.list_station_memory_records("Platform Readiness HTTP Test Station")
        require(any(item.get("virtual") and item.get("id", "").startswith("memory-admin-") for item in admin_records), "admin outlines should map into station memory records")

        print(json.dumps({
            "ok": True,
            "recordId": record_v1["id"],
            "alias": alias_context["name"],
            "snapshotVersion": snapshot.get("sourceVersion"),
            "adminMapped": len(admin_records),
        }, ensure_ascii=False, indent=2))
    finally:
        if original is None:
            if memory_path.exists():
                memory_path.unlink()
        else:
            memory_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    main()
