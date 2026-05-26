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
    spec = importlib.util.spec_from_file_location("interconnect_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def assert_truthy(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    server = load_server()
    transfer_station = next(
        item for item in server.STATIONS.get("stations", [])
        if "/" in str(item.get("lines") or "")
    )
    normal_station = next(
        item for item in server.STATIONS.get("stations", [])
        if "/" not in str(item.get("lines") or "") and item.get("name")
    )

    fragment = transfer_station["name"][:2] or transfer_station["name"]
    search = server.search_stations(fragment, limit=8)
    assert search["query"] == fragment
    assert search["count"] >= 1
    assert any(item["name"] == transfer_station["name"] for item in search["results"])
    top = search["results"][0]
    assert_truthy(top.get("sourceLabels"), "search results should expose source labels")
    assert_truthy(top.get("stationType"), "search results should include inferred station type")

    transfer_context = server.station_context_payload(transfer_station["name"])
    transfer_fields = transfer_context["suggestedFields"]
    assert transfer_context["ok"] is True
    assert transfer_fields["station.name"] == transfer_context["name"]
    assert transfer_fields["station.line"]
    assert transfer_fields["station.stationType"] == "current_transfer"
    assert_truthy(transfer_context.get("sources"), "context should distinguish data sources")

    normal_context = server.station_context_payload(normal_station["name"])
    normal_fields = normal_context["suggestedFields"]
    assert normal_fields["station.stationType"] == "normal"

    manual_context = server.station_context_payload(
        normal_station["name"],
        {"stationType": "planned_transfer", "line": normal_station.get("lines") or ""}
    )
    assert manual_context["suggestedFields"]["station.stationType"] == "planned_transfer"

    print(json.dumps({
        "ok": True,
        "transfer": transfer_context["name"],
        "normal": normal_context["name"],
        "searchCount": search["count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
