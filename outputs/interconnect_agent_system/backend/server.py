from __future__ import annotations

import json
import gzip
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from zipfile import ZIP_DEFLATED, ZipFile

try:
    from backend.research_agent import benchmark_cases_status, build_client_report, build_model_oriented_research
except ModuleNotFoundError:
    from research_agent import benchmark_cases_status, build_client_report, build_model_oriented_research


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"
EXPORT_DIR = ROOT / "exports"
PROJECTS_PATH = DATA_DIR / "projects.json"
SCHEMATIC_DIR = FRONTEND_DIR / "schematic"
SCHEMATIC_GEOMETRY_PATH = SCHEMATIC_DIR / "user_geometry.json"
SCHEMATIC_EXPORT_DIR = SCHEMATIC_DIR / "exports"


def load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_json_optional(name: str, default: dict) -> dict:
    path = DATA_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def amap_credentials() -> tuple[str, str]:
    key = os.environ.get("AMAP_JS_KEY", "")
    security_code = os.environ.get("AMAP_SECURITY_CODE", "")
    if key and security_code:
        return key, security_code
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
            if not key:
                key = winreg.QueryValueEx(env_key, "AMAP_JS_KEY")[0]
            if not security_code:
                security_code = winreg.QueryValueEx(env_key, "AMAP_SECURITY_CODE")[0]
    except Exception:
        pass
    return key, security_code


FACTORS = load_json("factors.json")
RULES = load_json("design_rules.json")
STATIONS = load_json("stations.json")
DEMOS = load_json("demo_cases.json")
RIDERSHIP = load_json_optional("ridership.json", {"records": []})
STATION_OPERATIONS = load_json_optional("station_operations.json", {"records": []})
STATION_AMENITIES = load_json_optional("station_amenities.json", {"records": []})
INPUT_SCHEMA = load_json_optional("input_schema.json", {"fields": []})
PPT_RULES = load_json_optional("ppt_rules_summary.json", {})
KNOWLEDGE_CATALOG = load_json_optional("knowledge/knowledge_catalog.json", {})
RULE_CARDS = load_json_optional("knowledge/rule_cards.json", {"cards": []})
STATION_KNOWLEDGE_INDEX = load_json_optional("knowledge/station_index.json", {"records": []})
SOURCE_MANIFEST = load_json_optional("knowledge/source_manifest.json", [])
UNPARSED_SOURCES = load_json_optional("knowledge/unparsed_sources.json", [])
STATION_INDEX = {item["name"]: item for item in STATIONS.get("stations", [])}


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_slug(value: str | None, fallback: str = "project") -> str:
    text = value or fallback
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text, flags=re.UNICODE).strip("-")
    return text[:80] or fallback


def station_aliases(name: str | None) -> list[str]:
    text = (name or "").strip()
    if not text:
        return []
    aliases = [text]
    aliases.extend(match.strip() for match in re.findall(r"[（(]([^）)]+)[）)]", text) if match.strip())
    no_paren = re.sub(r"[（(].*?[）)]", "", text).strip()
    if no_paren:
        aliases.append(no_paren)
    if no_paren.endswith("站"):
        aliases.append(no_paren[:-1])
    return list(dict.fromkeys(item for item in aliases if item))


def build_alias_index(records: list[dict], name_getter) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for record in records:
        names = name_getter(record)
        if isinstance(names, str):
            names = [names]
        for name in names or []:
            for alias in station_aliases(name):
                index.setdefault(alias, record)
    return index


RIDERSHIP_INDEX = build_alias_index(RIDERSHIP.get("records", []), lambda item: item.get("stationName", ""))
OPERATIONS_INDEX = build_alias_index(
    STATION_OPERATIONS.get("records", []),
    lambda item: [item.get("name", ""), *item.get("aliases", []), *item.get("displayNames", [])]
)
AMENITIES_INDEX = build_alias_index(
    STATION_AMENITIES.get("records", []),
    lambda item: [item.get("name", ""), *item.get("aliases", []), *item.get("displayNames", [])]
)


def lookup_station_context(index: dict[str, dict], name: str | None) -> dict | None:
    for alias in station_aliases(name):
        if alias in index:
            return index[alias]
    return None


def load_projects() -> dict:
    if not PROJECTS_PATH.exists():
        return {"version": "1.0", "projects": []}
    return json.loads(PROJECTS_PATH.read_text(encoding="utf-8-sig"))


def save_projects(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_project_summaries() -> list[dict]:
    data = load_projects()
    summaries = []
    for item in data.get("projects", []):
        project = item.get("project", {})
        result = item.get("result") or {}
        if not isinstance(result, dict):
            result = {}
        summaries.append({
            "id": item.get("id"),
            "name": project.get("name") or "未命名项目",
            "projectCode": project.get("projectCode") or "",
            "stationName": (project.get("station") or {}).get("name") or "",
            "level": result.get("level") or "",
            "score": result.get("score"),
            "recommendedType": ((result.get("recommendation") or {}).get("primary") or {}).get("name") or "",
            "updatedAt": item.get("updatedAt"),
            "createdAt": item.get("createdAt")
        })
    return sorted(summaries, key=lambda item: item.get("updatedAt") or "", reverse=True)


def score_overview_rows(result: dict) -> list[dict]:
    rows = []
    for dimension in result.get("dimensions") or []:
        factors = dimension.get("factors") or []
        key_factors = []
        source_basis = []
        assumed_names = []
        for factor in factors:
            key_factors.append(
                f"{factor.get('name') or ''}：{factor.get('label') or '待补齐'}"
                f"（{float(factor.get('weightedScore') or 0):.4f}）"
            )
            source_basis.append(
                f"{factor.get('name') or ''}：{factor.get('source') or '规则评分表/项目输入'}"
            )
            if factor.get("assumed"):
                assumed_names.append(factor.get("name") or "")
        rows.append({
            "dimension": dimension.get("name") or "",
            "score": float(dimension.get("score") or 0),
            "keyFactors": "；".join(key_factors),
            "sourceBasis": "；".join(source_basis),
            "note": f"含临时试算：{'、'.join(assumed_names)}" if assumed_names else "核心字段已取值"
        })
    return rows


def option_lookup(factor: dict) -> dict:
    return {option["value"]: option for option in factor.get("options", [])}


def iter_factors() -> list[tuple[dict, dict]]:
    pairs: list[tuple[dict, dict]] = []
    for dimension in FACTORS["dimensions"]:
        for factor in dimension["factors"]:
            pairs.append((dimension, factor))
    return pairs


FACTOR_LOOKUP = {factor["id"]: option_lookup(factor) for _, factor in iter_factors()}


def classify_development_intensity(building_area: float | int | None) -> str | None:
    if building_area is None:
        return None
    try:
        value = float(building_area)
    except (TypeError, ValueError):
        return None
    if value >= 100000:
        return "gt_100k"
    if value >= 30000:
        return "30k_100k"
    if value >= 5000:
        return "5k_30k"
    return "lt_5k"


def classify_ridership(daily_inbound: float | int | None) -> str | None:
    if daily_inbound is None:
        return None
    try:
        value = float(daily_inbound)
    except (TypeError, ValueError):
        return None
    if value >= 9000:
        return "gt_9000"
    if value >= 5000:
        return "5000_9000"
    if value >= 2500:
        return "2500_5000"
    return "lt_2500"


def resolve_station_context(station: dict) -> dict:
    station_name = station.get("name")
    ridership_record = lookup_station_context(RIDERSHIP_INDEX, station_name)
    operations_record = lookup_station_context(OPERATIONS_INDEX, station_name)
    amenities_record = lookup_station_context(AMENITIES_INDEX, station_name)

    input_daily = station.get("dailyInbound")
    try:
        input_daily_value = float(input_daily) if input_daily not in {None, ""} else None
    except (TypeError, ValueError):
        input_daily_value = None

    matched_latest = ridership_record.get("latestDailyInbound") if ridership_record else None
    if input_daily_value is not None:
        daily_inbound = input_daily_value
        if matched_latest is not None and abs(input_daily_value - float(matched_latest)) < 1:
            daily_source = f"每站每月日均进站.xlsx：{ridership_record.get('latestMonth') or '最新月'}日均进站"
        else:
            daily_source = "使用方输入：日均客流"
    elif ridership_record and ridership_record.get("latestDailyInbound") is not None:
        daily_inbound = float(ridership_record["latestDailyInbound"])
        daily_source = f"每站每月日均进站.xlsx：{ridership_record.get('latestMonth') or '最新月'}日均进站"
    else:
        daily_inbound = None
        daily_source = ""

    return {
        "dailyInbound": daily_inbound,
        "dailyInboundSource": daily_source,
        "ridership": ridership_record,
        "operations": operations_record,
        "amenities": amenities_record
    }


def max_weighted_score() -> float:
    configured = (FACTORS.get("scoreScale") or {}).get("rawMax")
    if configured:
        return float(configured)
    total = 0.0
    for _, factor in iter_factors():
        total += factor["weight"] * max(option["score"] for option in factor.get("options", []))
    return round(total, 4)


def normalized_score(score: float) -> float:
    max_score = max_weighted_score()
    if max_score <= 0:
        return 0.0
    return round(score / max_score * 100, 2)


def compact_nearby_places(amenities: dict) -> str:
    nearby = amenities.get("nearby") or {}
    labels = {
        "schools": "学校",
        "hubs": "交通/公益",
        "residential": "住宅",
        "commercial": "商业景点",
        "other": "其他"
    }
    parts = []
    for key, label in labels.items():
        values = [item for item in nearby.get(key, []) if item]
        if values:
            parts.append(f"{label}：{'、'.join(values[:2])}")
    return "；".join(parts)


def load_knowledge_chunks() -> list[dict]:
    path = DATA_DIR / "knowledge" / "knowledge_chunks.jsonl"
    if not path.exists():
        return []
    chunks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(json.loads(line))
    return chunks


def search_knowledge(
    query: str,
    limit: int = 20,
    category: str | None = None,
    kind: str | None = None,
    min_score: int | None = None
) -> dict:
    terms = [term.lower() for term in re.split(r"\s+", query.strip()) if term.strip()]
    if not terms:
        return {"query": query, "count": 0, "results": []}
    results = []
    for chunk in load_knowledge_chunks():
        haystack = f"{chunk.get('title', '')} {chunk.get('text', '')}".lower()
        if not all(term in haystack for term in terms):
            continue
        hits = sum(haystack.count(term) for term in terms)
        if hits:
            score = hits * 10 + len(terms) * 100 + int(chunk.get("priority") or 0)
            if category and chunk.get("category") != category:
                continue
            if kind and chunk.get("kind") != kind:
                continue
            if min_score is not None and score < min_score:
                continue
            results.append({
                "score": score,
                "sourcePath": chunk.get("sourcePath"),
                "sourceName": chunk.get("sourceName"),
                "title": chunk.get("title"),
                "category": chunk.get("category"),
                "kind": chunk.get("kind"),
                "text": chunk.get("text", "")[:700],
                "metadata": chunk.get("metadata") or {}
            })
    results.sort(key=lambda item: item["score"], reverse=True)
    return {"query": query, "count": len(results), "results": results[:limit]}


def infer_transfer(station: dict, preset: dict | None) -> str | None:
    station_type = station.get("stationType")
    if station_type in {"current_transfer", "planned_transfer", "normal"}:
        return station_type
    lines = str(station.get("line") or (preset or {}).get("lines") or "")
    if "/" in lines:
        return "current_transfer"
    if station.get("name") or preset:
        return "normal"
    return None


def infer_location(station: dict, preset: dict | None) -> str | None:
    explicit = station.get("locationLevel")
    if explicit in FACTOR_LOOKUP["location_level"]:
        return explicit
    preset_level = (preset or {}).get("locationLevel")
    if preset_level in FACTOR_LOOKUP["location_level"]:
        return preset_level
    return None


def grade_score(score: float, score_percent: float | None = None) -> dict:
    for grade in FACTORS["grading"]:
        if score_percent is not None and ("percentMin" in grade or "percentMax" in grade):
            min_value = grade.get("percentMin")
            max_value = grade.get("percentMax")
            value = score_percent
        else:
            min_value = grade["min"]
            max_value = grade["max"]
            value = score
        if (min_value is None or value >= min_value) and (max_value is None or value < max_value):
            return grade
    return FACTORS["grading"][-1]


def parse_line_count(value: str | None) -> int:
    parts = [item for item in re.split(r"[/、,，\s]+", str(value or "")) if item]
    return len(parts)


def numeric_value(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def pick_station_precheck_rule(station: dict | None, station_context: dict | None) -> str:
    station = station or {}
    station_context = station_context or {}
    operations = station_context.get("operations") or {}
    ridership = station_context.get("ridership") or {}
    forms = " ".join(operations.get("connectionForms") or [])
    inbound = numeric_value(station.get("dailyInbound") or ridership.get("latestDailyInbound"))
    line_count = parse_line_count(station.get("line") or ridership.get("lines"))
    location_level = station.get("locationLevel") or ""
    exit_count = int(operations.get("exitCount") or 0)

    if any(keyword in forms for keyword in ("高架", "天桥", "空中")):
        return "station_precheck_sky_bridge"
    if line_count >= 2 and inbound >= 9000 and location_level == "city":
        return "station_precheck_underground_main"
    if (line_count >= 2 and inbound >= 5000) or location_level == "city" or inbound >= 12000:
        return "station_precheck_underground_secondary"
    if location_level == "district" or inbound >= 5000 or exit_count >= 4:
        return "station_precheck_weather_corridor"
    return "fallback_surface"


def pick_rule(level: str, parcel: dict, missing: list[dict], station: dict | None = None, station_context: dict | None = None) -> dict:
    land_use = parcel.get("landUse")
    underground = parcel.get("undergroundSpace")
    has_critical_missing = any(item["factorId"] in {"land_use", "underground_space"} for item in missing)

    if has_critical_missing:
        rule_id = pick_station_precheck_rule(station, station_context)
    elif level == "必连地块" and underground == "commercial_public_pr":
        rule_id = "must_connect_public_underground"
    elif level == "尽连地块" and underground == "commercial_public_pr":
        rule_id = "priority_connect_public_underground"
    elif land_use in {"office_school_residential", "general_public_commercial"}:
        rule_id = "residential_or_apartment_surface"
    else:
        rule_id = "fallback_surface"

    return next(rule for rule in RULES["recommendationRules"] if rule["id"] == rule_id)


def type_by_id(type_id: str) -> dict:
    return next(item for item in RULES["connectionTypes"] if item["id"] == type_id)


def gap_detail(factor_id: str, station_context: dict | None = None) -> tuple[str, str]:
    station_context = station_context or {}
    operations = station_context.get("operations") or {}
    amenities = station_context.get("amenities") or {}
    if factor_id == "land_use":
        has_context = bool((operations.get("details") or []) or (amenities.get("nearby") or {}))
        if has_context:
            return (
                "未提供具体地块用地性质；运营表中的地块名称和周边配套已作为背景线索入库，但不能等同正式用地功能评分。",
                "缺正式地块用地性质；周边配套/地块名称仅作预评估线索"
            )
        return (
            "未提供具体地块用地性质，当前按保守 1 分临时试算。",
            "缺正式地块用地性质"
        )
    if factor_id == "development_intensity":
        return (
            "未提供建筑面积、用地面积、容积率或开发强度分档，当前按保守 1 分临时试算。",
            "缺建筑面积/容积率/开发强度正式指标"
        )
    if factor_id == "underground_space":
        forms = "、".join(operations.get("connectionForms") or [])
        if forms:
            return (
                f"运营表已识别联通形式：{forms}；但未提供地块地下空间功能、开放属性和接口标高，暂不作为地下空间因子正式赋值。",
                "有联通形式线索，缺地块地下空间正式条件"
            )
        return (
            "未提供地块地下空间功能、公共开放属性和接口条件，当前按保守 1 分临时试算。",
            "缺地块地下空间正式条件"
        )
    return (
        f"{factor_id}缺少可计算输入，当前按 1 分临时试算。",
        "系统保守预设，需补齐复核"
    )


def make_factor_value(
    factor: dict,
    value: str | None,
    missing: list[dict],
    source: str | None = None,
    station_context: dict | None = None
) -> dict:
    options = FACTOR_LOOKUP[factor["id"]]
    if value in options:
        option = options[value]
        return {
            "factorId": factor["id"],
            "name": factor["name"],
            "value": value,
            "label": option["label"],
            "score": option["score"],
            "weight": factor["weight"],
            "weightedScore": round(option["score"] * factor["weight"], 4),
            "assumed": False,
            "source": source or "现有输入/预设数据"
        }

    message, fallback_source = gap_detail(factor["id"], station_context)
    fallback = {
        "factorId": factor["id"],
        "name": factor["name"],
        "value": None,
        "label": "正式地块资料待补齐，暂按保守 1 分试算",
        "score": 1,
        "weight": factor["weight"],
        "weightedScore": round(factor["weight"], 4),
        "assumed": True,
        "source": fallback_source
    }
    missing.append({
        "factorId": factor["id"],
        "name": factor["name"],
        "message": message
    })
    return fallback


def evaluate_project(project: dict, research_options: dict | None = None) -> dict:
    station = project.get("station") or {}
    parcel = project.get("parcel") or {}
    preset_station = STATION_INDEX.get(station.get("name", ""))
    station_context = resolve_station_context(station)
    missing: list[dict] = []

    values = {
        "land_use": parcel.get("landUse"),
        "development_intensity": parcel.get("developmentIntensity") or classify_development_intensity(parcel.get("buildingArea")),
        "location_level": infer_location(station, preset_station),
        "ridership": classify_ridership(station_context.get("dailyInbound")),
        "transfer": infer_transfer(station, preset_station),
        "underground_space": parcel.get("undergroundSpace")
    }
    sources = {
        "ridership": station_context.get("dailyInboundSource") or None
    }

    dimension_results = []
    factor_results = []
    total_score = 0.0

    for dimension in FACTORS["dimensions"]:
        dimension_score = 0.0
        children = []
        for factor in dimension["factors"]:
            result = make_factor_value(
                factor,
                values.get(factor["id"]),
                missing,
                sources.get(factor["id"]),
                station_context
            )
            children.append(result)
            factor_results.append(result)
            dimension_score += result["weightedScore"]
        dimension_results.append({
            "id": dimension["id"],
            "name": dimension["name"],
            "weight": dimension["weight"],
            "score": round(dimension_score, 4),
            "factors": children
        })
        total_score += dimension_score

    score = round(total_score, 4)
    score_percent = normalized_score(score)
    grade = grade_score(score, score_percent)
    rule = pick_rule(grade["level"], parcel, missing, station, station_context)
    primary = type_by_id(rule["primary"])
    alternatives = [type_by_id(item) for item in rule["alternatives"]]
    recommendation_payload = {
        "primary": primary,
        "alternatives": alternatives,
        "rule": rule
    }

    llm_context = build_llm_review_context(
        project,
        score,
        score_percent,
        grade,
        dimension_results,
        primary,
        alternatives,
        rule,
        missing,
        station_context
    )
    research_bundle = build_model_oriented_research(
        project,
        score,
        score_percent,
        grade,
        dimension_results,
        recommendation_payload,
        missing,
        station_context,
        search_knowledge,
        research_options
    )
    model_judgement = research_bundle.get("modelJudgement") or {}
    model_rule_difference = research_bundle.get("modelRuleDifference") or {}
    model_quality = research_bundle.get("modelQuality") or {}
    diagram_brief = build_diagram_brief(project, {
        "level": grade["level"],
        "recommendation": recommendation_payload,
    }, model_judgement)
    report_modes = build_report_modes(model_judgement, model_rule_difference, model_quality)
    client_report_bundle = build_client_report(
        project,
        score,
        score_percent,
        grade,
        dimension_results,
        recommendation_payload,
        missing,
        station_context,
        research_bundle
    )
    report = build_report(
        project,
        score,
        score_percent,
        grade,
        dimension_results,
        primary,
        alternatives,
        rule,
        missing,
        station_context,
        llm_context,
        research_bundle
    )
    completeness_total = len(factor_results)
    completeness_done = sum(1 for item in factor_results if not item["assumed"])

    return {
        "project": project,
        "score": score,
        "scorePercent": score_percent,
        "scoreScale": FACTORS.get("scoreScale") or {"rawMax": max_weighted_score(), "normalizedMax": 100},
        "level": grade["level"],
        "policy": grade["policy"],
        "stationContext": station_context,
        "provisional": bool(missing),
        "dataCompleteness": {
            "done": completeness_done,
            "total": completeness_total,
            "ratio": round(completeness_done / completeness_total, 2)
        },
        "dimensions": dimension_results,
        "missing": missing,
        "recommendation": recommendation_payload,
        "researchPlan": research_bundle["researchPlan"],
        "evidencePack": research_bundle["evidencePack"],
        "modelAssessment": research_bundle["modelAssessment"],
        "modelJudgement": model_judgement,
        "modelRuleDifference": model_rule_difference,
        "modelQuality": model_quality,
        "diagramBrief": diagram_brief,
        "reportModes": report_modes,
        "capabilityStatus": research_bundle["capabilityStatus"],
        "clientReport": client_report_bundle["clientReport"],
        "clientReportMode": client_report_bundle["clientReportMode"],
        "llmReviewContext": llm_context,
        "report": report
    }


def join_cn(items: list[str], fallback: str = "暂无结构化记录") -> str:
    values = [str(item).strip() for item in items if item and str(item).strip()]
    return "；".join(values) if values else fallback


def factor_line(factor: dict) -> str:
    mark = "临时试算" if factor.get("assumed") else "已取值"
    return (
        f"{factor.get('name')}={factor.get('label')}，{factor.get('score')}分，"
        f"权重{factor.get('weight')}，加权{factor.get('weightedScore')}，来源：{factor.get('source')}，状态：{mark}"
    )


def build_reference_basis(project: dict, station_context: dict, missing: list[dict]) -> list[dict]:
    station = project.get("station") or {}
    references = [
        {
            "source": "互联互通智能体研发工作方案0318.pptx",
            "use": "确定近期目标、评价到报告的工作流、规则优先级和试点交付边界。",
            "status": "PPT规则源，优先于早期示例报告。"
        },
        {
            "source": "评价因子赋值明细表.xlsx",
            "use": "确定功能、区位、交通、地下四类维度、因子权重和选项赋值。",
            "status": "当前评分计算的直接依据。"
        },
        {
            "source": "20260507反馈",
            "use": "确认评分口径以Excel/PPT为准，早期样例报告仅作章节和表达参考。",
            "status": "验收口径确认。"
        },
        {
            "source": "车站TOD级别划分整理.xlsx",
            "use": f"提供{station.get('name') or '当前站点'}的TOD级别、线路和区位能级。",
            "status": "站点级预评估依据。"
        },
        {
            "source": "每站每月日均进站.xlsx",
            "use": "提供站点日均进站客流，用于交通属性中的出行客流因子。",
            "status": station_context.get("dailyInboundSource") or "未匹配客流时列为待补齐。"
        },
        {
            "source": "苏州地铁运营站点出入口、联通接口情况梳理统计表20260128.xlsx",
            "use": "提供出入口、接口、联通形式、开发进度和推进问题线索。",
            "status": "用于站点上下文和推荐规则分层，不替代正式地块资料。"
        },
        {
            "source": "运营公司车站出入口开放及周边配套统计表202604.xlsx",
            "use": "提供出入口开放、运营管理、周边学校/商业/住宅/公共设施等配套线索。",
            "status": "用于周边服务对象判断和资料补齐提示。"
        },
        {
            "source": "苏州轨道交通站点周边地下公共联通空间设计细则-结题评审修改稿.docx",
            "use": "作为地下联通空间、接口、无障碍、消防、运营界面等设计控制要求的知识库来源。",
            "status": "设计建议引用源，具体条款需在深化阶段人工复核。"
        }
    ]
    if missing:
        references.append({
            "source": "项目提资资料",
            "use": "补齐用地性质、建筑面积/容积率、地下空间功能、接口标高、权属边界和专项约束。",
            "status": f"当前仍有{len(missing)}项正式评分或项目资料待补齐。"
        })
    return references


def build_dimension_judgement(dimensions: list[dict]) -> list[dict]:
    judgements = []
    for dimension in dimensions:
        factors = dimension.get("factors") or []
        assumed = [factor.get("name") for factor in factors if factor.get("assumed")]
        score = float(dimension.get("score") or 0)
        if assumed:
            interpretation = f"{dimension.get('name')}含{join_cn(assumed, '')}临时试算，结论需随资料补齐复核。"
        elif score >= float(dimension.get("weight") or 0) * 3:
            interpretation = f"{dimension.get('name')}支撑度较强，对联通必要性形成正向贡献。"
        else:
            interpretation = f"{dimension.get('name')}贡献中等或偏弱，需结合工程条件和实施成本综合判断。"
        judgements.append({
            "id": dimension.get("id"),
            "name": dimension.get("name"),
            "weight": dimension.get("weight"),
            "score": dimension.get("score"),
            "factorEvidence": [factor_line(factor) for factor in factors],
            "interpretation": interpretation
        })
    return judgements


def build_scheme_comparison(primary: dict, alternatives: list[dict], rule: dict) -> list[dict]:
    schemes = [("推荐方案", primary)] + [(f"备选方案{index}", item) for index, item in enumerate(alternatives, 1)]
    comparison = []
    for role, scheme in schemes:
        comparison.append({
            "role": role,
            "name": scheme.get("name"),
            "category": scheme.get("category"),
            "reason": rule.get("reason") if role == "推荐方案" else "作为备选，用于接口、投资、交通组织或风貌约束变化时复核。",
            "bestFor": scheme.get("bestFor") or [],
            "avoidWhen": scheme.get("avoidWhen") or [],
            "technicalParameters": scheme.get("parameters") or []
        })
    return comparison


def build_diagram_brief(project: dict, result_facts: dict, judgement: dict) -> dict:
    station = (project.get("station") or {}).get("name") or "轨道站点"
    parcel = (project.get("parcel") or {}).get("name") or project.get("name") or "目标地块"
    scheme = (
        judgement.get("recommendedType")
        or ((result_facts.get("recommendation") or {}).get("primary") or {}).get("name")
        or "推荐联通方式"
    )
    return {
        "diagramId": "D-001",
        "diagramType": "recommended_connection_path",
        "title": "推荐联通路径示意",
        "summary": f"表达{station}与{parcel}之间的{scheme}关系，并标注主要风险与待复核界面。",
        "nodes": [
            {"id": "station", "label": station, "type": "station", "x": 110, "y": 160, "level": "B1"},
            {"id": "parcel", "label": parcel, "type": "parcel", "x": 430, "y": 160, "level": "B1"},
        ],
        "edges": [
            {"id": "path-1", "from": "station", "to": "parcel", "type": "recommended", "label": scheme}
        ],
        "annotations": [
            {"id": "risk-1", "text": "接口标高、消防分区、产权界面需复核", "anchorTo": "path-1"}
        ],
        "exports": ["svg", "png", "docx"],
    }


def build_report_modes(judgement: dict, difference: dict, quality: dict) -> list[dict]:
    return [
        {
            "id": "client_formal",
            "name": "客户正式版",
            "tone": "正式、稳健、可审阅",
            "focus": "结论、依据、风险、补资和实施建议",
            "sectionDensity": "medium",
            "qualityLabels": quality.get("labels", []),
        },
        {
            "id": "expert_appendix",
            "name": "专家附录版",
            "tone": "证据完整、规则透明、便于复核",
            "focus": "规则基线、模型差异、证据引用和复核问题",
            "sectionDensity": "high",
            "qualityLabels": difference.get("reviewLabels", []),
        },
        {
            "id": "leadership_brief",
            "name": "领导汇报版",
            "tone": "一页一结论、一页一风险、一页一行动",
            "focus": "模型结论、推荐方案、关键风险和下一步动作",
            "sectionDensity": "low",
            "qualityLabels": ["可汇报", *quality.get("labels", [])[:2]],
        },
    ]


def build_risk_points(project: dict, missing: list[dict], station_context: dict) -> list[dict]:
    operations = station_context.get("operations") or {}
    amenities = station_context.get("amenities") or {}
    risks = [
        {
            "topic": "正式地块资料",
            "point": "用地性质、建筑面积/容积率、地下空间功能缺失时，评分和推荐只能作为站点级预评估。",
            "action": "补齐控规图则、规划条件、地块指标和地下空间说明后复核。"
        },
        {
            "topic": "接口工程条件",
            "point": "接口位置、标高、非付费区关系、结构边界和防水节点决定推荐方式能否落地。",
            "action": "深化阶段需核对车站接口条件、地块地下室平面和竖向标高。"
        },
        {
            "topic": "消防与疏散",
            "point": "地下或封闭连通空间涉及防火分区、排烟、疏散距离、运营管理边界。",
            "action": "方案比选时同步校核消防专项和运营分界。"
        },
        {
            "topic": "无障碍与导向",
            "point": "步行接驳应保证连续无障碍、夜间照明、导向识别和客流组织清晰。",
            "action": "近期实施方案应先落实连续路径和标识系统。"
        },
        {
            "topic": "权属与施工界面",
            "point": "红线、产权、管线迁改、施工组织和费用分摊可能改变方案优先级。",
            "action": "把权属边界、施工时序和投资责任纳入补齐清单。"
        }
    ]
    if operations.get("issueCount"):
        risks.append({
            "topic": "既有推进问题",
            "point": f"运营资料记录问题{operations.get('issueCount')}条，可能影响接口开放或协议签署。",
            "action": "优先复核问题记录、接口费、联通协议和建设状态。"
        })
    if amenities and amenities.get("openExitCount") != amenities.get("exitRows"):
        risks.append({
            "topic": "出入口开放状态",
            "point": f"运营配套资料显示开放{amenities.get('openExitCount')}/{amenities.get('exitRows')}个。",
            "action": "核实现状可达性和未开放口对接条件。"
        })
    if missing:
        risks.append({
            "topic": "补齐后结论漂移",
            "point": f"当前{len(missing)}项缺口按保守值试算，补齐后评分等级和推荐方式可能变化。",
            "action": "保留本次预评估版本，补齐后生成复核版并对比分值变化。"
        })
    return risks


def build_llm_review_context(
    project: dict,
    score: float,
    score_percent: float,
    grade: dict,
    dimensions: list[dict],
    primary: dict,
    alternatives: list[dict],
    rule: dict,
    missing: list[dict],
    station_context: dict | None = None
) -> dict:
    station_context = station_context or {}
    project_name = project.get("name") or "待命名项目"
    references = build_reference_basis(project, station_context, missing)
    dimension_judgement = build_dimension_judgement(dimensions)
    scheme_comparison = build_scheme_comparison(primary, alternatives, rule)
    risk_points = build_risk_points(project, missing, station_context)
    return {
        "purpose": "供模型在规则基线、项目事实和证据材料基础上做最终综合研判，可在说明理由和复核标签后覆盖规则结论。",
        "guardrails": [
            "可以覆盖规则等级或推荐方式，但必须保留规则基线、覆盖理由、证据引用和人工复核标签。",
            "正式地块资料缺失时必须标注预评估性质，不得把站点周边线索当作地块正式输入。",
            "引用资料应说明来源和用途；无法确认的工程条件应进入补齐项或风险项。",
            "输出需区分近期可实施措施、中期深化设计和远期一体化预留。"
        ],
        "projectFacts": {
            "name": project_name,
            "station": (project.get("station") or {}).get("name"),
            "score": score,
            "scorePercent": round(score_percent, 2),
            "level": grade.get("level"),
            "policy": grade.get("policy"),
            "primaryRecommendation": primary.get("name"),
            "ruleReason": rule.get("reason"),
            "missingItems": [item.get("message") for item in missing]
        },
        "referenceBasis": references,
        "dimensionJudgement": dimension_judgement,
        "schemeComparison": scheme_comparison,
        "riskAndReviewPoints": risk_points,
        "suggestedOutputSchema": [
            "综合判断结论",
            "主要依据与引用来源",
            "推荐方案适用性说明",
            "备选方案触发条件",
            "风险与需补齐资料",
            "近期/中期/远期实施建议",
            "人工复核问题清单"
        ]
    }


def build_report(
    project: dict,
    score: float,
    score_percent: float,
    grade: dict,
    dimensions: list[dict],
    primary: dict,
    alternatives: list[dict],
    rule: dict,
    missing: list[dict],
    station_context: dict | None = None,
    llm_context: dict | None = None,
    research_bundle: dict | None = None
) -> list[dict]:
    station = project.get("station") or {}
    parcel = project.get("parcel") or {}
    station_context = station_context or {}
    operations = station_context.get("operations") or {}
    ridership = station_context.get("ridership") or {}
    amenities = station_context.get("amenities") or {}
    station_name = station.get("name") or "待补齐车站"
    project_name = project.get("name") or "待命名项目"
    missing_text = "；".join(item["message"] for item in missing) if missing else "当前核心评价字段完整"
    dimension_text = "；".join(f"{item['name']} {item['score']:.4f} 分" for item in dimensions)
    alt_text = "、".join(item["name"] for item in alternatives)
    params = "；".join(primary.get("parameters", [])[:4])
    raw_max = max_weighted_score()
    district = station.get("district") or "、".join((operations.get("districts") or [])[:2]) or "待补齐区划"
    site_area = parcel.get("siteArea") or "待补齐"
    building_area = parcel.get("buildingArea") or "待补齐"
    location = parcel.get("location") or parcel.get("quadrant") or "待补齐位置"
    land_use_text = parcel.get("functionalFormat") or parcel.get("landUseText") or "待补齐"
    planning = parcel.get("planningIndicators") or "待补齐规划指标"
    daily = station_context.get("dailyInbound")
    daily_text = (
        f"{daily:.0f} 人次/日（{station_context.get('dailyInboundSource')}）"
        if isinstance(daily, (int, float)) else "待补齐"
    )
    operation_text = (
        f"站点侧已识别出入口 {operations.get('exitCount', 0)} 个，"
        f"联通形式 {('、'.join(operations.get('connectionForms') or []) or '暂无结构化记录')}，"
        f"问题记录 {operations.get('issueCount', 0)} 条。"
        if operations else "出入口与接口信息待补齐。"
    )
    amenities_text = (
        f"运营公司202604资料显示，站点出入口开放 {amenities.get('openExitCount', 0)}/{amenities.get('exitRows', 0)} 个，"
        f"运营管理 {amenities.get('managedExitCount', 0)} 个；周边配套包括{compact_nearby_places(amenities) or '待补齐'}。"
        if amenities else "运营侧出入口开放和周边配套资料待补齐。"
    )
    ridership_note = (
        f"客流记录覆盖至 {ridership.get('latestMonth')}，平均日均进站 {ridership.get('averageDailyInbound')} 人次/日。"
        if ridership else "客流未匹配到站点预设记录。"
    )
    llm_context = llm_context or {}
    research_bundle = research_bundle or {}
    research_plan = research_bundle.get("researchPlan") or {}
    evidence_pack = research_bundle.get("evidencePack") or {}
    model_assessment = research_bundle.get("modelAssessment") or {}
    model_judgement = research_bundle.get("modelJudgement") or {}
    model_rule_difference = research_bundle.get("modelRuleDifference") or {}
    capability_status = research_bundle.get("capabilityStatus") or {}
    reference_text = "；".join(
        f"{item.get('source')}（{item.get('use')}）"
        for item in (llm_context.get("referenceBasis") or [])[:8]
    )
    dimension_judgement_text = "；".join(
        f"{item.get('name')}：{item.get('interpretation')}"
        for item in (llm_context.get("dimensionJudgement") or [])
    )
    comparison_text = "；".join(
        f"{item.get('role')}{item.get('name')}，适用：{join_cn(item.get('bestFor') or [], '待结合项目条件判断')}，回避：{join_cn(item.get('avoidWhen') or [], '暂无')}"
        for item in (llm_context.get("schemeComparison") or [])
    )
    risk_text = "；".join(
        f"{item.get('topic')}：{item.get('point')}建议：{item.get('action')}"
        for item in (llm_context.get("riskAndReviewPoints") or [])[:8]
    )
    llm_schema_text = "、".join(llm_context.get("suggestedOutputSchema") or [])
    capability_text = (
        f"本地缓存{(capability_status.get('localCache') or {}).get('mode', '未知')}，"
        f"独立搜索{(capability_status.get('independentSearch') or {}).get('mode', '未知')}，"
        f"模型{(capability_status.get('llm') or {}).get('mode', '未知')}，"
        f"模型联网{(capability_status.get('modelWebSearch') or {}).get('mode', '未知')}。"
    )
    research_questions_text = "；".join(
        item.get("question", "")
        for item in (research_plan.get("questions") or [])[:6]
        if item.get("question")
    )
    evidence_text = "；".join(
        f"{item.get('title')}（{item.get('source')}，置信度{item.get('confidence')}，{'缓存' if item.get('cached') else '实时'}）"
        for item in (evidence_pack.get("items") or [])[:10]
    )
    model_dimension_text = "；".join(
        f"{item.get('name')}：{item.get('judgement') or item.get('summary') or item.get('focus')}（置信度{item.get('confidence', '待确认')}）"
        for item in (model_assessment.get("dynamicDimensions") or [])[:8]
    )
    model_review_text = "；".join(model_assessment.get("reviewQuestions") or [])
    model_uncertainty_text = "；".join(model_assessment.get("uncertainties") or [])

    return [
        {
            "title": "项目概况与资料边界",
            "content": (
                f"{project_name}对应站点为{station_name}，所属区划为{district}，地块位置为{location}，"
                f"圈层为{parcel.get('distanceBand') or '待补齐'}。地块业态为{land_use_text}，"
                f"用地面积约{site_area}平方米，建筑面积约{building_area}平方米，规划指标为{planning}。"
                f"邻近出入口为{station.get('nearbyExit') or '待补齐'}，日均客流为{daily_text}。{operation_text}{amenities_text}"
                "本段仅描述已入库事实和待补齐资料边界，不把周边配套线索直接等同为地块正式评分输入。"
            )
        },
        {
            "title": "评价口径与引用依据",
            "content": (
                f"本次评价以PPT工作方案、评价因子赋值表和20260507反馈为主控口径，引用依据包括：{reference_text}。"
                "其中评分因子、权重和等级阈值由结构化规则引擎计算；设计细则、运营资料和周边配套作为解释、比选、风险识别和补齐项提示依据。"
            )
        },
        {
            "title": "站点能级、客流与接口研判",
            "content": (
                f"{station_name}的区位能级为{station.get('todLevel') or station.get('locationLevel') or '待补齐'}，"
                f"线路/换乘信息为{station.get('line') or '待补齐'}，日均客流为{daily_text}。{ridership_note}"
                f"{operation_text}这些信息用于判断站点侧联通需求、接口成熟度和近期实施抓手；若后续接入客流预测、客流方向、分时段拥挤度，可进一步细化为路径级方案建议。"
            )
        },
        {
            "title": "周边功能与服务对象研判",
            "content": (
                f"运营公司202604资料和站点周边索引显示，周边配套包括{compact_nearby_places(amenities) or '待补齐'}。"
                "这些内容可辅助判断服务对象、全天候需求、导向标识和步行系统连续性，但仍需控规、规划条件和地块方案确认具体用地功能、开发强度和地下空间条件。"
            )
        },
        {
            "title": "多维度评分拆解",
            "content": (
                f"本次按功能、区位、交通、地下四个维度进行参数化试算，维度得分为：{dimension_text}。"
                f"维度解释为：{dimension_judgement_text}。"
                "对临时试算因子，系统保留1分保守值并在待补齐项中说明原因，避免用推断数据替代正式资料。"
            )
        },
        {
            "title": "联通必要性评估结论",
            "content": (
                f"原始加权分为 {score:.4f}/{raw_max:.4f}，折算百分制为 {score_percent:.2f} 分，"
                f"按 20260507 反馈的 80/60 阈值判定为{grade['level']}。{grade['policy']}{ridership_note}"
                "该结论表示当前资料条件下的必要性等级；若后续补齐地块规模、地下空间或接口条件，系统应重新计算并输出差异说明。"
            )
        },
        {
            "title": "推荐方案与方案比选",
            "content": (
                f"系统推荐采用{primary['name']}，推荐理由为：{rule['reason']}。"
                f"备选方案包括{alt_text}。比选框架为：{comparison_text}。"
                "后续可按接口可达性、投资强度、施工影响、全天候服务、运营管理和城市风貌六类指标做专家复核。"
            )
        },
        {
            "title": "方案设计核心技术要求",
            "content": (
                f"{primary['name']}属于{primary['category']}方式。核心技术要求包括：{params}。"
                "深化设计还应明确通行净宽、净高、坡道/电梯、导向标识、照明、排水、防滑、运营管理界面和应急疏散组织。"
            )
        },
        {
            "title": "风险约束与专项复核",
            "content": (
                f"重点风险和复核建议包括：{risk_text}。"
                "上述风险不直接否定推荐方案，但会影响方案层级、接口形式、建设时序和投资责任划分。"
            )
        },
        {
            "title": "智能研究计划与能力状态",
            "content": (
                f"系统按“规则保底、实时研究、本地知识兜底、模型增强”的策略生成研究计划，当前能力状态为：{capability_text}"
                f"匹配标杆案例为{(research_plan.get('benchmarkCase') or {}).get('label', '通用站点互联互通预评估')}。"
                f"本轮研究问题包括：{research_questions_text}。"
                "模型可用时以模型综合研判为主，本地资料作为证据弹药；未连接模型时需用户确认后才使用离线兜底。"
            )
        },
        {
            "title": "证据包与来源置信度",
            "content": (
                f"本轮证据包模式为{evidence_pack.get('mode', 'offline_cache')}，"
                f"共收集{(evidence_pack.get('summary') or {}).get('total', 0)}条证据，"
                f"其中缓存{(evidence_pack.get('summary') or {}).get('cached', 0)}条、实时{(evidence_pack.get('summary') or {}).get('live', 0)}条。"
                f"代表性证据包括：{evidence_text}。"
                "证据优先级为项目正式输入/规则源、本地标杆缓存、独立搜索、模型联网低置信补充；未被印证的外部信息只作为复核线索。"
            )
        },
        {
            "title": "模型导向多维研判",
            "content": (
                f"{model_assessment.get('summary') or '当前采用本地兜底研判。'}"
                f"动态维度研判包括：{model_dimension_text}。"
                f"不确定性包括：{model_uncertainty_text or '暂无额外不确定性'}。"
                f"人工复核问题包括：{model_review_text}。"
                "上述模型导向研判以模型为最终综合判断，规则评分作为基线和差异检查坐标保留。"
            )
        },
        {
            "title": "模型主导综合研判",
            "content": (
                f"模型主结论为：{model_judgement.get('level', grade['level'])}，推荐方式为"
                f"{model_judgement.get('recommendedType', primary.get('name'))}。"
                f"置信度约为{model_judgement.get('confidence', 0):.2f}。"
                f"判断理由：{model_judgement.get('reason', '模型基于规则基线、站点上下文和资料证据形成综合判断。')}"
                f"差异状态：{model_rule_difference.get('status', 'aligned')}；"
                f"复核标签：{join_cn(model_rule_difference.get('reviewLabels') or [])}。"
            )
        },
        {
            "title": "资料补齐与复核路径",
            "content": (
                f"资料完整性状态：{missing_text}。建议在方案深化前补齐站点客流、接口标高、出入口位置、地下空间功能、"
                "建设时序和特殊约束条件。补齐后应重新运行评分，并输出补齐前后等级、推荐方式和关键因子变化。"
            )
        },
        {
            "title": "实施时序与协同建议",
            "content": (
                "近期建议先形成可落地的步行接驳、导向标识、接口预留和资料补齐清单；中期结合地块方案、地下空间和接口标高做工程可行性比选；"
                "远期在片区更新或地块开发同步阶段推动站城一体化连通、运营管理界面和投资责任机制。"
                "责任协同建议覆盖轨道运营、规划设计、地块开发主体、道路/市政/管线单位和消防审查单位。"
            )
        },
        {
            "title": "LLM综合判断框架",
            "content": (
                "后续接入其他LLM时，建议把本次后端结果作为规则基线、证据包和差异检查输入，LLM负责最终综合研判、方案复核和专家式建议。"
                f"输入应包括项目事实、引用依据、四维评分拆解、推荐与备选方案、风险复核点和待补齐资料。建议输出结构为：{llm_schema_text}。"
                "模型可以在明确说明理由、证据和复核标签的前提下覆盖规则等级或推荐方案；规则评分作为基线和差异检查坐标保留。"
                "模型不得把缺失资料补成确定事实；所有新增判断应标注依据、置信度和需人工确认的问题。"
            )
        }
    ]


def build_markdown_report(result: dict) -> str:
    project = result.get("project") or {}
    title = project.get("name") or "互联互通评估报告"
    primary = ((result.get("recommendation") or {}).get("primary") or {}).get("name") or "待推荐"
    raw_max = ((result.get("scoreScale") or {}).get("rawMax") or max_weighted_score())
    lines = [
        f"# {title}",
        "",
        f"- 地块编号：{project.get('projectCode') or '待补齐'}",
        f"- 综合评分（百分制）：{float(result.get('scorePercent') or 0):.2f}分",
        f"- 原始加权分：{float(result.get('score') or 0):.4f} / {float(raw_max):.4f}",
        f"- 联通等级：{result.get('level') or '待判定'}",
        f"- 推荐方式：{primary}",
        f"- 数据完整度：{(result.get('dataCompleteness') or {}).get('done', 0)}/{(result.get('dataCompleteness') or {}).get('total', 0)}",
        ""
    ]
    lines.extend([
        "## 评分总览",
        "",
        "| 项目 | 结果 |",
        "| --- | --- |",
        f"| 综合评分（百分制） | {float(result.get('scorePercent') or 0):.2f}分 |",
        f"| 原始加权分 | {float(result.get('score') or 0):.4f} / {float(raw_max):.4f} |",
        f"| 联通等级 | {result.get('level') or '待判定'} |",
        f"| 推荐方式 | {primary} |",
        f"| 数据完整度 | {(result.get('dataCompleteness') or {}).get('done', 0)}/{(result.get('dataCompleteness') or {}).get('total', 0)} |",
        "",
        "| 评分维度 | 加权得分 | 主要因子取值 | 来源依据 | 说明 |",
        "| --- | ---: | --- | --- | --- |",
    ])
    for row in score_overview_rows(result):
        lines.append(
            f"| {row['dimension']} | {row['score']:.4f} | "
            f"{row['keyFactors'].replace('|', '/')} | "
            f"{row['sourceBasis'].replace('|', '/')} | {row['note']} |"
        )
    lines.append("")
    client_sections = result.get("clientReport") or result.get("report") or []
    for index, section in enumerate(client_sections, 1):
        lines.extend([f"## {index}. {section.get('title')}", "", section.get("content") or "", ""])
    missing = result.get("missing") or []
    if missing:
        lines.extend(["## 资料补齐与复核事项", ""])
        for item in missing:
            lines.append(f"- {item.get('name')}：{item.get('message')}")
        lines.append("")
    return "\n".join(lines)


def save_project_record(project: dict, research_options: dict | None = None) -> dict:
    research_options = research_options or {}
    data = load_projects()
    now = utc_now()
    record_id = project.get("id") or uuid.uuid4().hex[:12]
    existing = next((item for item in data.get("projects", []) if item.get("id") == record_id), None)
    result = (existing or {}).get("result")
    if not research_options.get("skipEvaluation"):
        result = evaluate_project(project, research_options)
    record = {
        "id": record_id,
        "project": project,
        "result": result,
        "createdAt": (existing or {}).get("createdAt") or now,
        "updatedAt": now
    }
    projects = [item for item in data.get("projects", []) if item.get("id") != record_id]
    projects.append(record)
    data["projects"] = projects
    save_projects(data)
    return record


def find_project_record(record_id: str, refresh: bool = False) -> dict | None:
    record = next((item for item in load_projects().get("projects", []) if item.get("id") == record_id), None)
    if record and refresh:
        record["result"] = evaluate_project(record.get("project") or {})
    return record


def delete_project_record(record_id: str) -> bool:
    data = load_projects()
    before = len(data.get("projects", []))
    data["projects"] = [item for item in data.get("projects", []) if item.get("id") != record_id]
    if len(data["projects"]) == before:
        return False
    save_projects(data)
    return True


def resolve_project_payload(payload: dict) -> tuple[dict, dict]:
    if isinstance(payload.get("project"), dict):
        return payload["project"], payload.get("researchOptions") or {}
    return payload, payload.get("researchOptions") or {}


def resolve_export_result(payload: dict) -> dict:
    project = payload.get("project")
    project_id = payload.get("projectId")
    legacy_result = payload.get("result")
    research_options = payload.get("researchOptions") or {}

    if project_id:
        record = find_project_record(str(project_id))
        if not record:
            raise ValueError("Project not found for export")
        project = record.get("project") or {}
    elif not isinstance(project, dict) and isinstance(legacy_result, dict):
        project = legacy_result.get("project")
    elif not isinstance(project, dict):
        project = payload

    if not isinstance(project, dict):
        raise ValueError("Export requires a project payload")
    return evaluate_project(project, research_options)


def export_report_file(result: dict) -> dict:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    project = result.get("project") or {}
    slug = safe_slug(project.get("projectCode") or project.get("name"), "interconnect-report")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    files = []
    snapshot_file = EXPORT_DIR / f"{slug}-{stamp}-evaluation-snapshot.json"
    snapshot_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append(file_info(snapshot_file))
    report_docx = create_docx_report(result, slug, stamp)
    score_docx = create_score_detail_docx(result, slug, stamp)
    for docx_file in [report_docx, score_docx]:
        if not docx_file:
            continue
        files.append(file_info(docx_file))
        pdf_file = create_pdf_from_docx(docx_file)
        if pdf_file:
            files.append(file_info(pdf_file))

    return {
        "filename": report_docx.name if report_docx else "",
        "path": str(report_docx) if report_docx else "",
        "relativePath": str(report_docx.relative_to(ROOT)) if report_docx else "",
        "files": files
    }


def csv_escape(value: str) -> str:
    if any(char in value for char in [",", "\"", "\n"]):
        return "\"" + value.replace("\"", "\"\"") + "\""
    return value


def file_info(path: Path) -> dict:
    return {
        "filename": path.name,
        "path": str(path),
        "relativePath": str(path.relative_to(ROOT)),
        "size": path.stat().st_size
    }


def export_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith("-score-detail.docx"):
        return "打分明细 Word"
    if name.endswith("-score-detail.pdf"):
        return "打分明细 PDF"
    if name.endswith("-formal-report.docx"):
        return "正式报告 Word"
    if name.endswith("-formal-report.pdf"):
        return "正式报告 PDF"
    if name.endswith(".pdf"):
        return "PDF 报告"
    if name.endswith(".docx"):
        return "Word 报告"
    if name.endswith(".md"):
        return "Markdown 报告"
    if name.endswith(".json"):
        return "评估快照"
    if name.endswith("-score-detail.csv"):
        return "评分明细"
    if name.endswith("-missing.csv"):
        return "待补齐清单"
    if name.endswith(".csv"):
        return "CSV 数据"
    return "导出文件"


def list_export_files(limit: int = 40) -> list[dict]:
    if not EXPORT_DIR.exists():
        return []
    files = [
        path for path in EXPORT_DIR.iterdir()
        if (
            path.is_file()
            and path.suffix.lower() in {".docx", ".pdf"}
            and (
                path.name.lower().endswith("-formal-report.docx")
                or path.name.lower().endswith("-formal-report.pdf")
                or path.name.lower().endswith("-score-detail.docx")
                or path.name.lower().endswith("-score-detail.pdf")
            )
        )
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    items = []
    for path in files[:limit]:
        info = file_info(path)
        info["kind"] = export_kind(path)
        info["updatedAt"] = datetime.fromtimestamp(path.stat().st_mtime).replace(microsecond=0).isoformat()
        items.append(info)
    return items


def manifest_file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "filename": path.name,
        "relativePath": path.relative_to(ROOT).as_posix(),
        "size": stat.st_size,
        "updatedAt": datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat()
    }


def existing_files(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        files.append(path)
    return files


def delivery_manifest_groups() -> list[dict]:
    doc_files = existing_files([
        ROOT / "docs" / "delivery_notes.md",
        ROOT / "docs" / "acceptance_report.md",
        ROOT / "docs" / "api_reference.md",
        ROOT / "docs" / "delivery_manifest.md",
        ROOT / "docs" / "function_and_gap_inventory.md",
        ROOT / "docs" / "knowledge_database.md",
        ROOT / "docs" / "feedback_20260507_analysis.md",
        ROOT / "docs" / "llm_integration_contract.md",
        ROOT / "docs" / "pilot_input_template.xlsx",
    ])
    runtime_files = existing_files([
        ROOT / "README.md",
        ROOT / "run.ps1",
        ROOT / "backend" / "server.py",
        ROOT / "backend" / "research_agent.py",
        ROOT / "verify_system.cjs",
        ROOT / "tools" / "seed_station_projects.py",
        ROOT / "tools" / "verify_station_precheck.cjs",
        ROOT / "tools" / "verify_report_richness.cjs",
        ROOT / "tools" / "verify_model_oriented_research.py",
        ROOT / "tools" / "verify_client_report.py",
    ])
    screenshot_files = existing_files([
        ROOT / "interconnect_dashboard.png",
        ROOT / "interconnect_assessment.png",
        ROOT / "interconnect_knowledge.png",
        ROOT / "interconnect_reporting.png",
        ROOT / "interconnect_agent_screenshot.png",
    ])
    mockup_files = existing_files([
        ROOT / "docs" / "mockups" / "dashboard-concept-20260508.png",
        ROOT / "docs" / "mockups" / "dashboard-ideal.png",
        ROOT / "docs" / "mockups" / "assessment-ideal.png",
        ROOT / "docs" / "mockups" / "knowledge-ideal.png",
        ROOT / "docs" / "mockups" / "report-completion-ideal.png",
    ])
    export_files = [ROOT / item["relativePath"] for item in list_export_files(20)]
    groups = [
        ("runtime", "运行与验收入口", runtime_files),
        ("docs", "交付文档", doc_files),
        ("screenshots", "验收截图", screenshot_files),
        ("mockups", "理想页面视觉稿", mockup_files),
        ("exports", "最近导出成果", existing_files(export_files)),
    ]
    return [
        {
            "id": group_id,
            "title": title,
            "files": [manifest_file_info(path) for path in files],
        }
        for group_id, title, files in groups
    ]


def build_delivery_manifest_payload() -> dict:
    groups = delivery_manifest_groups()
    files = [item for group in groups for item in group["files"]]
    total_size = sum(item["size"] for item in files)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return {
        "generatedAt": utc_now(),
        "totalFiles": len(files),
        "totalSize": total_size,
        "groups": groups,
        "files": files,
        "package": {
            "filename": f"interconnect-agent-delivery-{stamp}.zip",
            "downloadUrl": "/api/delivery/package",
        },
    }


def build_delivery_package() -> tuple[str, bytes]:
    manifest = build_delivery_manifest_payload()
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("delivery_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in manifest["files"]:
            path = ROOT / item["relativePath"]
            if path.exists() and path.is_file():
                archive.write(path, item["relativePath"])
    return manifest["package"]["filename"], buffer.getvalue()


def set_doc_defaults(doc) -> None:
    from docx.shared import Pt

    styles = doc.styles
    styles["Normal"].font.name = "Microsoft YaHei"
    styles["Normal"].font.size = Pt(10.5)


def create_score_detail_docx(result: dict, slug: str, stamp: str) -> Path | None:
    try:
        from docx import Document
    except Exception:
        return None

    target = EXPORT_DIR / f"{slug}-{stamp}-score-detail.docx"
    project = result.get("project") or {}
    raw_max = ((result.get("scoreScale") or {}).get("rawMax") or max_weighted_score())

    doc = Document()
    set_doc_defaults(doc)
    doc.add_heading(f"{project.get('name') or '互联互通评估'}打分明细", 0)
    doc.add_paragraph(f"地块编号：{project.get('projectCode') or '待补齐'}")
    doc.add_paragraph(f"综合评分（百分制）：{float(result.get('scorePercent') or 0):.2f}分")
    doc.add_paragraph(f"原始加权分：{float(result.get('score') or 0):.4f} / {float(raw_max):.4f}")
    doc.add_paragraph(f"联通等级：{result.get('level') or '待判定'}")

    table = doc.add_table(rows=1, cols=8)
    headers = table.rows[0].cells
    for index, label in enumerate(["维度", "因子", "选项", "原始分", "权重", "加权分", "来源", "是否假定"]):
        headers[index].text = label

    for dimension in result.get("dimensions") or []:
        for factor in dimension.get("factors") or []:
            cells = table.add_row().cells
            values = [
                dimension.get("name") or "",
                factor.get("name") or "",
                factor.get("label") or "",
                str(factor.get("score") or ""),
                str(factor.get("weight") or ""),
                str(factor.get("weightedScore") or ""),
                factor.get("source") or "",
                "是" if factor.get("assumed") else "否",
            ]
            for index, value in enumerate(values):
                cells[index].text = value

    missing = result.get("missing") or []
    doc.add_heading("资料缺项", level=1)
    if missing:
        missing_table = doc.add_table(rows=1, cols=3)
        missing_headers = missing_table.rows[0].cells
        missing_headers[0].text = "因子"
        missing_headers[1].text = "名称"
        missing_headers[2].text = "说明"
        for item in missing:
            cells = missing_table.add_row().cells
            cells[0].text = item.get("factorId") or ""
            cells[1].text = item.get("name") or ""
            cells[2].text = item.get("message") or ""
    else:
        doc.add_paragraph("当前核心评分字段完整，导出前仍建议结合正式设计条件进行人工复核。")

    doc.save(target)
    return target


def create_pdf_from_docx(docx_path: Path) -> Path | None:
    pdf_path = docx_path.with_suffix(".pdf")
    if convert_docx_to_pdf_with_word(docx_path, pdf_path):
        return pdf_path
    if convert_docx_to_pdf_with_libreoffice(docx_path, pdf_path):
        return pdf_path
    if create_simple_pdf_from_docx_text(docx_path, pdf_path):
        return pdf_path
    return None


def convert_docx_to_pdf_with_word(docx_path: Path, pdf_path: Path) -> bool:
    try:
        import pythoncom
        from win32com import client
    except Exception:
        return False

    word = None
    document = None
    try:
        pythoncom.CoInitialize()
        word = client.DispatchEx("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(docx_path.resolve()))
        document.ExportAsFixedFormat(str(pdf_path.resolve()), 17)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False
    finally:
        try:
            if document is not None:
                document.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def convert_docx_to_pdf_with_libreoffice(docx_path: Path, pdf_path: Path) -> bool:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        return False
    try:
        subprocess.run(
            [
                executable,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf_path.parent),
                str(docx_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except Exception:
        return False
    converted = docx_path.with_suffix(".pdf")
    return converted.exists() and converted.stat().st_size > 0


def create_simple_pdf_from_docx_text(docx_path: Path, pdf_path: Path) -> bool:
    try:
        import fitz
        from docx import Document
    except Exception:
        return False

    try:
        source = Document(docx_path)
        lines: list[str] = []
        for paragraph in source.paragraphs:
            text = paragraph.text.strip()
            if text:
                lines.extend(textwrap.wrap(text, width=48) or [text])
                lines.append("")
        for table in source.tables:
            for row in table.rows:
                text = " | ".join(cell.text.strip().replace("\n", " ") for cell in row.cells)
                lines.extend(textwrap.wrap(text, width=48) or [text])
            lines.append("")

        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        x, y = 54, 54
        for line in lines or [docx_path.stem]:
            if y > 790:
                page = pdf.new_page(width=595, height=842)
                y = 54
            page.insert_text((x, y), line, fontname="china-s", fontsize=10)
            y += 16
        pdf.save(pdf_path)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def create_docx_report(result: dict, slug: str, stamp: str) -> Path | None:
    try:
        from docx import Document
        from docx.shared import Pt
    except Exception:
        return None

    target = EXPORT_DIR / f"{slug}-{stamp}-formal-report.docx"
    project = result.get("project") or {}
    primary = ((result.get("recommendation") or {}).get("primary") or {}).get("name") or "待推荐"

    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Microsoft YaHei"
    styles["Normal"].font.size = Pt(10.5)
    doc.add_heading(project.get("name") or "互联互通评估报告", 0)
    doc.add_paragraph(f"地块编号：{project.get('projectCode') or '待补齐'}")
    raw_max = ((result.get("scoreScale") or {}).get("rawMax") or max_weighted_score())
    doc.add_paragraph(f"综合评分（百分制）：{float(result.get('scorePercent') or 0):.2f}分")
    doc.add_paragraph(f"原始加权分：{float(result.get('score') or 0):.4f} / {float(raw_max):.4f}")
    doc.add_paragraph(f"联通等级：{result.get('level') or '待判定'}")
    doc.add_paragraph(f"推荐方式：{primary}")
    doc.add_paragraph(
        f"数据完整度：{(result.get('dataCompleteness') or {}).get('done', 0)}/"
        f"{(result.get('dataCompleteness') or {}).get('total', 0)}"
    )

    doc.add_heading("评分总览", level=1)
    summary_table = doc.add_table(rows=1, cols=2)
    summary_headers = summary_table.rows[0].cells
    summary_headers[0].text = "项目"
    summary_headers[1].text = "结果"
    summary_items = [
        ("综合评分（百分制）", f"{float(result.get('scorePercent') or 0):.2f}分"),
        ("原始加权分", f"{float(result.get('score') or 0):.4f} / {float(raw_max):.4f}"),
        ("联通等级", result.get("level") or "待判定"),
        ("推荐方式", primary),
        ("数据完整度", f"{(result.get('dataCompleteness') or {}).get('done', 0)}/{(result.get('dataCompleteness') or {}).get('total', 0)}"),
    ]
    for label, value in summary_items:
        row = summary_table.add_row().cells
        row[0].text = label
        row[1].text = value

    dimension_table = doc.add_table(rows=1, cols=5)
    dimension_headers = dimension_table.rows[0].cells
    dimension_headers[0].text = "评分维度"
    dimension_headers[1].text = "加权得分"
    dimension_headers[2].text = "主要因子取值"
    dimension_headers[3].text = "来源依据"
    dimension_headers[4].text = "说明"
    for item in score_overview_rows(result):
        row = dimension_table.add_row().cells
        row[0].text = item["dimension"]
        row[1].text = f"{item['score']:.4f}"
        row[2].text = item["keyFactors"]
        row[3].text = item["sourceBasis"]
        row[4].text = item["note"]

    recommendation = result.get("recommendation") or {}
    primary = recommendation.get("primary") or {}
    alternatives = recommendation.get("alternatives") or []
    doc.add_heading("推荐方案与备选方案", level=1)
    rec_table = doc.add_table(rows=1, cols=4)
    rec_headers = rec_table.rows[0].cells
    rec_headers[0].text = "类型"
    rec_headers[1].text = "名称"
    rec_headers[2].text = "类别"
    rec_headers[3].text = "核心适用场景"
    row = rec_table.add_row().cells
    row[0].text = "推荐"
    row[1].text = primary.get("name") or ""
    row[2].text = primary.get("category") or ""
    row[3].text = "、".join(primary.get("bestFor") or [])
    for item in alternatives:
        row = rec_table.add_row().cells
        row[0].text = "备选"
        row[1].text = item.get("name") or ""
        row[2].text = item.get("category") or ""
        row[3].text = "、".join(item.get("bestFor") or [])

    client_sections = result.get("clientReport") or result.get("report") or []
    for index, section in enumerate(client_sections, 1):
        doc.add_heading(f"{index}. {section.get('title')}", level=1)
        doc.add_paragraph(section.get("content") or "")

    missing = result.get("missing") or []
    if missing:
        doc.add_heading("资料补齐与复核事项", level=1)
        table = doc.add_table(rows=1, cols=3)
        headers = table.rows[0].cells
        headers[0].text = "因子"
        headers[1].text = "名称"
        headers[2].text = "说明"
        for item in missing:
            cells = table.add_row().cells
            cells[0].text = item.get("factorId") or ""
            cells[1].text = item.get("name") or ""
            cells[2].text = item.get("message") or ""
    doc.save(target)
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "InterconnectAgent/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/api/health":
            self._json({"ok": True, "service": "interconnect-agent", "version": FACTORS["version"]})
            return
        if route == "/api/knowledge":
            self._json({
                "ok": True,
                "catalog": KNOWLEDGE_CATALOG,
                "ruleCards": {
                    "count": len(RULE_CARDS.get("cards", [])),
                    "sample": RULE_CARDS.get("cards", [])[:8]
                },
                "stationIndex": {
                    "count": STATION_KNOWLEDGE_INDEX.get("count", 0),
                    "coverage": STATION_KNOWLEDGE_INDEX.get("coverage", {})
                },
                "sources": SOURCE_MANIFEST,
                "unparsedSources": UNPARSED_SOURCES
            })
            return
        if route == "/api/knowledge/search":
            params = parse_qs(parsed.query)
            query = (params.get("q") or [""])[0]
            limit = int((params.get("limit") or ["20"])[0])
            category = (params.get("category") or [""])[0] or None
            kind = (params.get("kind") or params.get("evidenceType") or [""])[0] or None
            min_score_text = (params.get("minScore") or params.get("minConfidence") or [""])[0]
            try:
                min_score = int(float(min_score_text)) if min_score_text else None
            except ValueError:
                min_score = None
            self._json({
                "ok": True,
                **search_knowledge(query, min(max(limit, 1), 50), category, kind, min_score),
                "filters": {
                    "category": category,
                    "kind": kind,
                    "minScore": min_score
                }
            })
            return
        if route == "/api/research/benchmark-cases":
            self._json({"ok": True, **benchmark_cases_status()})
            return
        if route == "/api/bootstrap":
            self._json({
                "factors": FACTORS,
                "rules": RULES,
                "stations": STATIONS,
                "ridership": RIDERSHIP,
                "stationOperations": STATION_OPERATIONS,
                "stationAmenities": STATION_AMENITIES,
                "inputSchema": INPUT_SCHEMA,
                "pptRules": PPT_RULES,
                "knowledgeCatalog": KNOWLEDGE_CATALOG,
                "sourceManifest": SOURCE_MANIFEST,
                "unparsedSources": UNPARSED_SOURCES,
                "demos": DEMOS,
                "projects": list_project_summaries(),
                "exports": list_export_files(20)
            })
            return
        if route == "/api/sources":
            self._json({
                "ok": True,
                "catalog": KNOWLEDGE_CATALOG,
                "sources": SOURCE_MANIFEST,
                "unparsedSources": UNPARSED_SOURCES
            })
            return
        if route == "/api/exports":
            self._json({"ok": True, "exports": list_export_files(80)})
            return
        if route == "/api/schematic/user-geometry":
            self._schematic_user_geometry()
            return
        if route == "/api/delivery/manifest":
            self._json({"ok": True, **build_delivery_manifest_payload()})
            return
        if route == "/api/delivery/package":
            filename, data = build_delivery_package()
            self._binary(data, "application/zip", filename)
            return
        if route == "/api/projects":
            self._json({"ok": True, "projects": list_project_summaries()})
            return
        if route.startswith("/api/projects/"):
            record_id = unquote(route.rsplit("/", 1)[-1])
            record = find_project_record(record_id)
            if not record:
                self.send_error(HTTPStatus.NOT_FOUND, "Project not found")
                return
            self._json({"ok": True, "record": record})
            return
        if route.startswith("/exports/"):
            self._export_static(route)
            return
        self._static(route)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/schematic/user-geometry":
            self._save_schematic_user_geometry()
            return
        if route == "/api/schematic/export-png":
            self._export_schematic_png()
            return
        if route not in {"/api/evaluate", "/api/projects", "/api/export"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
            payload = json.loads(body.decode("utf-8") or "{}")
            if route == "/api/evaluate":
                project, research_options = resolve_project_payload(payload)
                result = evaluate_project(project, research_options)
                self._json({"ok": True, "result": result})
                return
            if route == "/api/projects":
                project, research_options = resolve_project_payload(payload)
                record = save_project_record(project, research_options)
                self._json({"ok": True, "record": record, "projects": list_project_summaries()})
                return
            result = resolve_export_result(payload)
            export = export_report_file(result)
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._json({"ok": True, "export": export})

    def do_DELETE(self) -> None:
        route = urlparse(self.path).path
        if not route.startswith("/api/projects/"):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        record_id = unquote(route.rsplit("/", 1)[-1])
        if not delete_project_record(record_id):
            self.send_error(HTTPStatus.NOT_FOUND, "Project not found")
            return
        self._json({"ok": True, "projects": list_project_summaries()})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write((fmt % args) + "\n")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        accepts_gzip = "gzip" in (self.headers.get("Accept-Encoding") or "").lower()
        if accepts_gzip:
            data = gzip.compress(data, compresslevel=6)
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if accepts_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _binary(self, data: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(HTTPStatus.OK)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        if not body:
            return {}
        return json.loads(body.decode("utf-8") or "{}")

    def _schematic_user_geometry(self) -> None:
        if not SCHEMATIC_GEOMETRY_PATH.exists():
            self._json({"ok": False, "geometry": None})
            return
        self._binary(SCHEMATIC_GEOMETRY_PATH.read_bytes(), "application/json; charset=utf-8")

    def _save_schematic_user_geometry(self) -> None:
        try:
            payload = self._read_json_body()
            if not isinstance(payload, dict) or "parcel" not in payload:
                raise ValueError("geometry payload must include parcel")
            SCHEMATIC_DIR.mkdir(parents=True, exist_ok=True)
            SCHEMATIC_GEOMETRY_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._json({"ok": True, "path": str(SCHEMATIC_GEOMETRY_PATH)})
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _export_schematic_png(self) -> None:
        try:
            SCHEMATIC_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["AMAP_EXPORT_URL"] = "http://127.0.0.1:8765/schematic/index.html?view=3d&export=1"
            node_modules = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "node_modules"
            if node_modules.exists() and not env.get("NODE_PATH"):
                env["NODE_PATH"] = str(node_modules)
            completed = subprocess.run(
                ["node", str(SCHEMATIC_DIR / "export_current_view.cjs")],
                cwd=str(SCHEMATIC_DIR),
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=75,
            )
            if completed.returncode != 0:
                self._json(
                    {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            stdout = completed.stdout or ""
            if not stdout.strip() and (SCHEMATIC_DIR / "last_export.json").exists():
                stdout = (SCHEMATIC_DIR / "last_export.json").read_text(encoding="utf-8")
            self._json(json.loads(stdout))
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _static(self, route: str) -> None:
        if route in {"", "/"}:
            target = FRONTEND_DIR / "index.html"
        else:
            relative = unquote(route.lstrip("/"))
            target = (FRONTEND_DIR / relative).resolve()
            if not str(target).startswith(str(FRONTEND_DIR.resolve())):
                self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target == (SCHEMATIC_DIR / "index.html").resolve():
            key, security_code = amap_credentials()
            html = target.read_text(encoding="utf-8")
            html = html.replace("__AMAP_JS_KEY__", key)
            html = html.replace("__AMAP_SECURITY_CODE__", security_code)
            data = html.encode("utf-8")
            mime = "text/html; charset=utf-8"
        else:
            data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _export_static(self, route: str) -> None:
        relative = unquote(route.removeprefix("/exports/"))
        target = (EXPORT_DIR / relative).resolve()
        if not str(target).startswith(str(EXPORT_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Export not found")
            return
        data = target.read_bytes()
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    if "--host" in sys.argv:
        host = sys.argv[sys.argv.index("--host") + 1]
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"http://{host}:{port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
