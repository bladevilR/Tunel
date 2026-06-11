from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import server  # noqa: E402


def assert_true(condition, message, detail=None) -> None:
    if not condition:
        raise AssertionError(json.dumps({"message": message, "detail": detail}, ensure_ascii=False, indent=2))


def main() -> None:
    capabilities = server.build_platform_capability_status()
    for key in ("generatedImage", "accounts", "adminStationOutlines", "deployment"):
        assert_true(key in capabilities, f"missing platform capability: {key}", capabilities)
        assert_true("enabled" in capabilities[key], f"capability should expose enabled flag: {key}", capabilities[key])

    placeholder = server.generated_image_placeholder({"prompt": "station connection rendering"})
    assert_true(placeholder["ok"] is False, "image API placeholder should be disabled by default", placeholder)
    assert_true(placeholder["error"]["code"] == "not_configured", "image API should return structured not_configured error", placeholder)
    disabled_response = server.generated_image_response({"prompt": "station connection rendering"})
    assert_true(disabled_response["ok"] is False, "image API response should be disabled by default", disabled_response)
    assert_true(disabled_response["error"]["code"] == "not_configured", "disabled image API response should be structured", disabled_response)

    validation = server.validate_server_configuration()
    assert_true("resolved" in validation, "server validation should expose resolved config", validation)
    assert_true(validation["resolved"]["host"], "server validation should include host", validation)

    identity = server.local_identity_payload()
    assert_true(identity["identity"]["type"] == "anonymous", "local identity should be anonymous", identity)
    assert_true(identity["identity"]["id"], "local identity should expose a stable id", identity)

    station_name = "平台准备度测试站"
    outline = server.save_admin_station_outline({
        "stationName": station_name,
        "outline": {
            "id": "admin-outline-platform-test",
            "name": "平台准备度测试站站体",
            "path": [[120.1, 31.1], [120.2, 31.1], [120.2, 31.2], [120.1, 31.2]],
        },
        "source": {"type": "admin", "operator": "platform-readiness-test"},
    })
    assert_true(outline["stationName"] == station_name, "admin outline should be saved with station name", outline)
    outlines = server.list_admin_station_outlines(station_name)
    assert_true(any(item["id"] == outline["id"] for item in outlines), "admin outline should be listed", outlines)

    applied = server.apply_admin_station_outline_to_geometry({"stationOutlines": []}, station_name, outline["id"])
    assert_true(applied["applied"] is True, "admin outline should apply to project geometry", applied)
    geometry = applied["geometry"]
    assert_true(geometry["stationOutlines"], "applied geometry should include station outline", geometry)
    assert_true(geometry["stationOutlines"][0]["source"]["kind"] == "admin_station_outline", "applied outline should preserve source metadata", geometry)

    doc = ROOT / "docs" / "deployment_server_migration.md"
    assert_true(doc.exists() and doc.stat().st_size > 500, "deployment/server migration doc should exist", doc)
    text = doc.read_text(encoding="utf-8")
    for term in ("INTERCONNECT_HOST", "INTERCONNECT_PORT", "data", "exports", "AMAP_JS_KEY", "OPENAI_API_KEY", "runtime", "GENERATED_IMAGE_PROVIDER"):
        assert_true(term in text, f"deployment doc missing term: {term}", text[:1200])

    print(json.dumps({"ok": True, "capabilities": capabilities}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
