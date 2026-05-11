from __future__ import annotations

import importlib.util
import json
import re
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "backend" / "server.py"
PROJECTS_PATH = ROOT / "data" / "projects.json"


def load_server():
    spec = importlib.util.spec_from_file_location("interconnect_backend", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load backend server module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_slug(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value, flags=re.UNICODE).strip("-")
    return text[:70] or "station"


def first_text(values: list[str] | None) -> str:
    return next((item.strip() for item in values or [] if item and item.strip()), "")


def compact_nearby(amenities: dict | None) -> str:
    nearby = (amenities or {}).get("nearby") or {}
    values: list[str] = []
    for key in ["schools", "hubs", "residential", "commercial", "other"]:
        values.extend(item.strip() for item in nearby.get(key, []) if item and item.strip())
    return "；".join(values[:3])


def operation_summary(operations: dict | None) -> str:
    if not operations:
        return ""
    forms = "、".join(operations.get("connectionForms") or []) or "暂无结构化联通形式"
    return (
        f"运营资料识别出入口{operations.get('exitCount', 0)}个、"
        f"接口{operations.get('interfaceCount', 0)}个；联通形式：{forms}；"
        f"问题记录{operations.get('issueCount', 0)}条。"
    )


def build_project(server, station: dict) -> dict:
    name = station.get("name") or "未命名站点"
    operations = server.lookup_station_context(server.OPERATIONS_INDEX, name) or {}
    amenities = server.lookup_station_context(server.AMENITIES_INDEX, name) or {}
    ridership = server.lookup_station_context(server.RIDERSHIP_INDEX, name) or {}
    district = first_text(operations.get("districts")) or first_text(amenities.get("districts")) or ""
    sample_exit = ((amenities.get("sampleExits") or [{}])[0] or {}).get("exit") or ""
    nearby = compact_nearby(amenities)
    interface_condition = operation_summary(operations) or "站点出入口接口条件待项目提资确认。"
    daily_inbound = ridership.get("latestDailyInbound")

    return {
        "id": f"station-{safe_slug(name)}",
        "name": f"{name}站周边互联互通预评估",
        "projectCode": f"STATION-{safe_slug(name)}",
        "station": {
            "name": name,
            "district": district,
            "line": station.get("lines") or first_text(ridership.get("lines")) or "",
            "todLevel": station.get("todLevel") or "",
            "locationLevel": station.get("locationLevel") or "",
            "stationType": "",
            "constructionState": "站点级预评估",
            "nearbyExit": sample_exit,
            "interfaceCondition": interface_condition,
            "dailyInbound": round(float(daily_inbound)) if isinstance(daily_inbound, (int, float)) else None,
        },
        "parcel": {
            "location": f"{name}站周边",
            "quadrant": "",
            "distanceBand": "200m核心开发区",
            "landUse": "",
            "landUseText": "待项目提资明确具体地块用地性质",
            "functionalFormat": nearby or "待项目提资明确周边业态",
            "siteArea": None,
            "buildingArea": None,
            "developmentIntensity": "",
            "undergroundSpace": "",
            "undergroundDescription": "待项目提资明确地下空间、接口标高和非付费区条件",
            "planningIndicators": "",
            "functionalDemand": "基于站点客流、TOD级别、出入口开放和周边配套先行预评估",
            "constraints": "控规图则、规划条件、概念方案、接口标高、管线和权属边界待补齐",
        },
        "attachments": "",
    }


def main() -> None:
    server = load_server()
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    projects = []
    seen: set[str] = set()
    for station in server.STATIONS.get("stations", []):
        project = build_project(server, station)
        if project["id"] in seen:
            suffix = 2
            base = project["id"]
            while f"{base}-{suffix}" in seen:
                suffix += 1
            project["id"] = f"{base}-{suffix}"
            project["projectCode"] = project["id"].upper()
        seen.add(project["id"])
        result = server.evaluate_project(project)
        projects.append({
            "id": project["id"],
            "project": project,
            "result": result,
            "createdAt": now,
            "updatedAt": now,
            "batchSeed": "stations-240",
        })

    payload = {
        "version": "1.0",
        "generatedAt": now,
        "source": "data/stations.json",
        "note": "240个站点级预评估项目；缺少具体地块提资的字段保持待补齐。",
        "projects": projects,
    }
    PROJECTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    levels: dict[str, int] = {}
    missing_counts: dict[int, int] = {}
    for record in projects:
        result = record["result"]
        levels[result["level"]] = levels.get(result["level"], 0) + 1
        missing_counts[len(result.get("missing") or [])] = missing_counts.get(len(result.get("missing") or []), 0) + 1
    print(json.dumps({
        "ok": True,
        "projects": len(projects),
        "levels": levels,
        "missingFactorCounts": missing_counts,
        "path": str(PROJECTS_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
