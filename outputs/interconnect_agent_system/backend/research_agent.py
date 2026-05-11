from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Callable
from urllib import error, parse, request


SearchFn = Callable[[str, int], dict]


BENCHMARK_CASES = [
    {
        "id": "jinjiayan-neighborhood-center",
        "label": "地下联通商业公服标杆",
        "station": "金家堰",
        "scenario": "商业公服地块具备地下公共空间，优先校核地下主通道、下沉广场和地下中庭。",
        "dimensions": ["地下公共空间", "商业公服服务对象", "接口竖向", "全天候接驳", "运营分界"],
        "queries": ["金家堰 邻里中心 地下 联通", "地下公共空间 轨道站点 商业公服 接口"]
    },
    {
        "id": "qingshuwan-youth-apartment",
        "label": "地面/风雨连廊社区居住标杆",
        "station": "清树湾",
        "scenario": "青年公寓和社区商业以稳定通勤、无障碍和经济可实施接驳为重点。",
        "dimensions": ["居住通勤", "风雨连廊", "慢行连续性", "社区商业引流", "近期实施"],
        "queries": ["清树湾 青年公寓 轨道 接驳", "风雨连廊 地铁 出入口 社区"]
    },
    {
        "id": "station-乐桥",
        "label": "城市级换乘高客流标杆",
        "station": "乐桥",
        "scenario": "城市级TOD、换乘和高客流站点需要优先识别地下接口、客流组织和古城风貌约束。",
        "dimensions": ["换乘客流", "城市级TOD", "地下通道", "古城风貌", "人流集散"],
        "queries": ["乐桥站 换乘 客流 地下通道", "苏州 乐桥 站城融合"]
    },
    {
        "id": "station-阳澄湖中路",
        "label": "高架天桥联通标杆",
        "station": "阳澄湖中路",
        "scenario": "既有资料显示高架联通线索，应重点校核天桥净空、结构、二层平台和景观影响。",
        "dimensions": ["高架联通", "桥下净空", "结构跨度", "景观影响", "二层平台"],
        "queries": ["阳澄湖中路 高架联通 地铁", "轨道站点 天桥 连廊 净空"]
    },
    {
        "id": "station-高铁苏州北站",
        "label": "交通枢纽站城融合标杆",
        "station": "高铁苏州北站",
        "scenario": "枢纽站点需兼顾铁路、轨道、公交、慢行和片区开发的一体化组织。",
        "dimensions": ["综合交通枢纽", "多方式换乘", "站城融合", "片区开发", "导向系统"],
        "queries": ["高铁苏州北站 枢纽 站城融合", "综合交通枢纽 地铁 联通 空间"]
    }
]


BASE_DYNAMIC_DIMENSIONS = [
    {
        "id": "city_interface",
        "name": "城市界面与站城融合",
        "focus": "站点与地块、道路、公共空间之间是否形成连续开放界面。"
    },
    {
        "id": "walking_accessibility",
        "name": "慢行可达与无障碍连续性",
        "focus": "步行距离、过街阻隔、风雨遮蔽、无障碍和导向是否完整。"
    },
    {
        "id": "service_population",
        "name": "服务对象与功能复合",
        "focus": "商业、公服、居住、学校、医院、枢纽等人群需求是否稳定。"
    },
    {
        "id": "engineering_interface",
        "name": "工程接口与竖向条件",
        "focus": "站厅非付费区、地下室、标高、防水、结构和管线条件是否支持落地。"
    },
    {
        "id": "operation_management",
        "name": "运营管理与安全边界",
        "focus": "消防、疏散、运营分界、开放时段、安防和维护责任是否清晰。"
    },
    {
        "id": "implementation_timing",
        "name": "实施时序与投资协同",
        "focus": "近期接驳、中期接口预留、远期一体化开发的协同路径是否清楚。"
    }
]

REPORT_REFERENCE_RULES = [
    "可引用本地设计细则中的控制要求：联通主通道净宽不宜小于5m、净高不宜小于3m；兼有商业设施时应结合单侧/双侧布置提高净宽，兼有休憩功能时净高宜提高。",
    "可引用本地设计指引中的控制要求：普通通道净宽不宜小于4m、净高不宜小于2.5m；兼有休憩功能时净宽不宜小于4.5m、净高不宜小于3m。",
    "可引用本地设计指引中的控制要求：联通空间应以无障碍为出发点，保持视线通透，并设置导向标识设施。",
    "可引用本地设计指引中的控制要求：地面风雨连廊应结合场地消防组织，满足消防通道与救援相关要求。",
    "涉及国家规范时，只能使用通用表述或已知规范名称，例如现行建筑防火、无障碍、地铁设计、地下空间、消防疏散等规范；不得编造不存在的标准编号、条文号或强制性条款。"
]


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def compact_text(value: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def station_name(project: dict) -> str:
    return ((project.get("station") or {}).get("name") or "").strip()


def project_id(project: dict) -> str:
    return (project.get("id") or project.get("projectCode") or project.get("name") or "").strip()


def match_benchmark_case(project: dict) -> dict:
    pid = project_id(project)
    station = station_name(project)
    for case in BENCHMARK_CASES:
        if pid == case["id"] or station == case["station"] or case["station"] in station:
            return {**case, "matched": True}
    return {
        "id": "general-station-interconnect",
        "label": "通用站点互联互通预评估",
        "station": station,
        "scenario": "未命中特定标杆案例时，按通用站城联通、慢行可达、接口风险和实施时序进行兜底研判。",
        "dimensions": ["站城融合", "慢行可达", "接口风险", "运营管理", "资料补齐"],
        "queries": [f"{station} 地铁 互联互通", "轨道站点 周边 联通 设计"],
        "matched": False
    }


def build_research_plan(project: dict, station_context: dict, dimensions: list[dict], missing: list[dict]) -> dict:
    station = station_name(project) or "当前站点"
    parcel = project.get("parcel") or {}
    benchmark = match_benchmark_case(project)
    missing_names = [item.get("name") for item in missing if item.get("name")]
    questions = [
        {
            "id": "station_role",
            "question": f"{station}在TOD等级、线路换乘、客流和片区功能中承担什么角色？",
            "evidenceTypes": ["station_index", "ridership", "tod_plan", "live_search"],
            "priority": "high"
        },
        {
            "id": "surrounding_functions",
            "question": "周边商业、公服、居住、学校、医院、枢纽等服务对象是否形成稳定联通需求？",
            "evidenceTypes": ["station_amenities", "live_search", "benchmark_cache"],
            "priority": "high"
        },
        {
            "id": "interface_feasibility",
            "question": "车站非付费区、出入口、地块地下室和竖向标高是否支持推荐联通方式？",
            "evidenceTypes": ["station_interface", "design_guidance", "project_input"],
            "priority": "high"
        },
        {
            "id": "scheme_benchmark",
            "question": f"当前项目与“{benchmark['label']}”相比，哪些维度应借鉴、哪些条件需复核？",
            "evidenceTypes": ["benchmark_cache", "local_knowledge"],
            "priority": "medium"
        },
        {
            "id": "risk_constraints",
            "question": "消防疏散、运营界面、管线权属、风貌景观和建设时序有哪些不确定性？",
            "evidenceTypes": ["design_guidance", "live_search", "manual_review"],
            "priority": "medium"
        },
        {
            "id": "data_gap_impact",
            "question": "正式提资缺项会如何影响评分等级、方案优先级和实施建议？",
            "evidenceTypes": ["project_input", "rule_engine", "missing_items"],
            "priority": "high" if missing else "medium"
        }
    ]
    if parcel.get("functionalFormat"):
        questions.append({
            "id": "parcel_format",
            "question": f"地块业态“{parcel.get('functionalFormat')}”对全天候接驳、导向和运营边界提出哪些特定要求？",
            "evidenceTypes": ["project_input", "benchmark_cache", "live_search"],
            "priority": "medium"
        })

    dynamic_dimensions = [dict(item) for item in BASE_DYNAMIC_DIMENSIONS]
    for label in benchmark.get("dimensions", []):
        dim_id = "benchmark_" + re.sub(r"\W+", "_", label, flags=re.UNICODE).strip("_").lower()
        if not any(item["name"] == label for item in dynamic_dimensions):
            dynamic_dimensions.append({
                "id": dim_id,
                "name": label,
                "focus": f"来自{benchmark['label']}的专项观察维度。"
            })

    return {
        "generatedAt": utc_now(),
        "strategy": "实时优先；联网或模型失败时使用本地知识库与五类标杆案例缓存兜底。",
        "benchmarkCase": benchmark,
        "questions": questions,
        "dimensions": dynamic_dimensions,
        "tasks": [
            {"id": "project_input", "name": "读取项目正式输入与缺项", "channel": "rule_engine", "required": True},
            {"id": "local_knowledge", "name": "检索本地规则、设计导则、站点和运营资料", "channel": "local_cache", "required": True},
            {"id": "benchmark_cache", "name": "匹配五类标杆案例知识包", "channel": "local_cache", "required": True},
            {"id": "independent_search", "name": "调用独立搜索接口获取实时外部证据", "channel": "live_search", "required": False},
            {"id": "model_web_search", "name": "如模型具备联网能力，补充模型侧外搜观点", "channel": "model_web", "required": False},
            {"id": "model_assessment", "name": "模型或本地兜底生成动态维度研判", "channel": "llm_or_fallback", "required": True}
        ],
        "missingSensitiveFactors": missing_names
    }


def local_fact_evidence(project: dict, station_context: dict, dimensions: list[dict], recommendation: dict, missing: list[dict]) -> list[dict]:
    station = station_name(project) or "当前站点"
    items = []
    items.append({
        "id": "rule-score",
        "type": "rule_fact",
        "source": "评价因子赋值明细表.xlsx / 后端规则引擎",
        "title": "规则评分与等级",
        "summary": "综合评分、百分制得分、必连/尽连/可连等级和推荐方式由规则引擎计算，模型不得改写。",
        "confidence": 1.0,
        "cached": True,
        "priority": 100
    })
    items.append({
        "id": "station-ridership",
        "type": "local_knowledge",
        "source": station_context.get("dailyInboundSource") or "每站每月日均进站.xlsx",
        "title": f"{station}客流线索",
        "summary": f"日均进站约{station_context.get('dailyInbound') or '待补齐'}，用于判断交通需求和路径组织强度。",
        "confidence": 0.92 if station_context.get("dailyInbound") else 0.45,
        "cached": True,
        "priority": 92
    })
    operations = station_context.get("operations") or {}
    if operations:
        items.append({
            "id": "station-interface",
            "type": "local_knowledge",
            "source": "苏州地铁运营站点出入口、联通接口情况梳理统计表20260128.xlsx",
            "title": f"{station}出入口与联通接口",
            "summary": f"识别出入口{operations.get('exitCount', 0)}个，联通形式{('、'.join(operations.get('connectionForms') or []) or '暂无结构化记录')}，问题记录{operations.get('issueCount', 0)}条。",
            "confidence": 0.9,
            "cached": True,
            "priority": 90
        })
    amenities = station_context.get("amenities") or {}
    if amenities:
        nearby = amenities.get("nearby") or {}
        nearby_text = "；".join(
            f"{key}:{'、'.join(values[:3])}"
            for key, values in nearby.items()
            if isinstance(values, list) and values
        )
        items.append({
            "id": "station-amenities",
            "type": "local_knowledge",
            "source": "运营公司车站出入口开放及周边配套统计表202604.xlsx",
            "title": f"{station}周边配套",
            "summary": compact_text(nearby_text or "周边配套未形成结构化摘要。"),
            "confidence": 0.86,
            "cached": True,
            "priority": 86
        })
    for dimension in dimensions:
        factors = dimension.get("factors") or []
        assumed = [factor.get("name") for factor in factors if factor.get("assumed")]
        items.append({
            "id": f"dimension-{dimension.get('id')}",
            "type": "rule_dimension",
            "source": "后端四维评分明细",
            "title": f"{dimension.get('name')}维度",
            "summary": f"得分{dimension.get('score')}；临时试算因子：{'、'.join(assumed) if assumed else '无'}。",
            "confidence": 0.88 if not assumed else 0.68,
            "cached": True,
            "priority": 80
        })
    primary = (recommendation.get("primary") or {}).get("name")
    rule = recommendation.get("rule") or {}
    if primary:
        items.append({
            "id": "recommendation-rule",
            "type": "rule_fact",
            "source": "design_rules.json",
            "title": f"推荐方式：{primary}",
            "summary": rule.get("reason") or "按推荐规则命中。",
            "confidence": 0.9,
            "cached": True,
            "priority": 88
        })
    if missing:
        items.append({
            "id": "missing-impact",
            "type": "risk",
            "source": "项目提资缺项",
            "title": "资料缺项影响",
            "summary": f"当前{len(missing)}项资料缺口会影响评分复核和方案深化，报告需标注预评估性质。",
            "confidence": 0.95,
            "cached": True,
            "priority": 85
        })
    return items


def benchmark_evidence(benchmark: dict) -> list[dict]:
    items = [{
        "id": f"benchmark-{benchmark['id']}",
        "type": "benchmark_cache",
        "source": "五类标杆案例知识包",
        "title": benchmark["label"],
        "summary": benchmark["scenario"],
        "confidence": 0.84 if benchmark.get("matched") else 0.65,
        "cached": True,
        "priority": 82
    }]
    for index, dimension in enumerate(benchmark.get("dimensions", []), 1):
        items.append({
            "id": f"benchmark-{benchmark['id']}-{index}",
            "type": "benchmark_dimension",
            "source": "五类标杆案例知识包",
            "title": dimension,
            "summary": f"作为{benchmark['label']}的专项研判维度，用于补足固定评分维度之外的模型观察。",
            "confidence": 0.78,
            "cached": True,
            "priority": 70
        })
    return items


def local_knowledge_evidence(plan: dict, search_local: SearchFn | None) -> list[dict]:
    if not search_local:
        return []
    queries = []
    benchmark = plan.get("benchmarkCase") or {}
    queries.extend(benchmark.get("queries") or [])
    queries.extend(["地下公共联通 空间 设计", "风雨连廊 无障碍 导向", "消防 疏散 运营 分界"])
    items = []
    seen = set()
    for query in queries[:6]:
        try:
            payload = search_local(query, 4)
        except Exception as exc:
            items.append({
                "id": f"local-search-error-{len(items)}",
                "type": "local_search_error",
                "source": "data/knowledge/knowledge_chunks.jsonl",
                "title": f"本地检索失败：{query}",
                "summary": str(exc),
                "confidence": 0.2,
                "cached": True,
                "priority": 20
            })
            continue
        for result in payload.get("results", [])[:3]:
            key = (result.get("sourceName"), result.get("title"), result.get("text"))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "id": f"local-knowledge-{len(items) + 1}",
                "type": "local_search",
                "source": result.get("sourceName") or result.get("sourcePath") or "本地知识库",
                "title": result.get("title") or query,
                "summary": compact_text(result.get("text"), 260),
                "query": query,
                "confidence": min(0.86, 0.55 + float(result.get("score") or 0) / 1000),
                "cached": True,
                "priority": int(result.get("score") or 50)
            })
    return items


def http_json(url: str, headers: dict, payload: dict | None = None, timeout: float = 6.0) -> dict:
    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
        headers = {**headers, "Content-Type": "application/json"}
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return json.loads(body) if body.strip() else {}


def run_independent_search(plan: dict) -> tuple[list[dict], dict]:
    base_url = os.environ.get("SEARCH_API_URL", "").strip()
    api_key = os.environ.get("SEARCH_API_KEY", "").strip()
    if not base_url or not api_key:
        return [], {"available": False, "mode": "not_configured", "reason": "SEARCH_API_URL 或 SEARCH_API_KEY 未配置"}

    started = time.time()
    headers = {"Authorization": f"Bearer {api_key}"}
    items = []
    errors = []
    queries = (plan.get("benchmarkCase") or {}).get("queries") or []
    for query in queries[:3]:
        try:
            url = base_url
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}q={parse.quote(query)}"
            payload = http_json(url, headers, timeout=5.0)
            results = payload.get("results") or payload.get("items") or payload.get("data") or []
            if isinstance(results, dict):
                results = results.get("results") or results.get("items") or []
            for result in results[:3]:
                title = result.get("title") or result.get("name") or query
                url_value = result.get("url") or result.get("link") or result.get("href") or base_url
                snippet = result.get("snippet") or result.get("summary") or result.get("content") or ""
                items.append({
                    "id": f"live-search-{len(items) + 1}",
                    "type": "independent_search",
                    "source": url_value,
                    "title": title,
                    "summary": compact_text(snippet or title),
                    "query": query,
                    "confidence": 0.62,
                    "cached": False,
                    "priority": 60
                })
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            errors.append({"query": query, "error": str(exc)})

    return items, {
        "available": bool(items),
        "mode": "live" if items else "failed",
        "reason": "" if items else "独立搜索未返回可用结果",
        "errors": errors,
        "elapsedMs": round((time.time() - started) * 1000)
    }


def llm_configured() -> bool:
    return all(os.environ.get(name, "").strip() for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def call_llm_json(messages: list[dict], timeout: float = 8.0, max_tokens: int = 1200) -> dict:
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    url = base_url
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    response = http_json(url, {"Authorization": f"Bearer {api_key}"}, payload, timeout=timeout)
    content = (((response.get("choices") or [{}])[0].get("message") or {}).get("content") or "{}")
    return parse_llm_json_content(content)


def parse_llm_json_content(content: str) -> dict:
    text = (content or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start():])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("模型返回内容未包含可解析 JSON 对象")


def run_model_assessment(
    project: dict,
    result_facts: dict,
    plan: dict,
    evidence_items: list[dict]
) -> tuple[dict | None, dict, list[dict]]:
    if not llm_configured():
        return None, {"available": False, "mode": "not_configured", "reason": "LLM_BASE_URL、LLM_API_KEY 或 LLM_MODEL 未配置"}, []

    compact_plan = {
        "strategy": plan.get("strategy"),
        "benchmarkCase": plan.get("benchmarkCase"),
        "questions": (plan.get("questions") or [])[:6],
        "dimensions": [
            {"name": item.get("name"), "focus": item.get("focus")}
            for item in (plan.get("dimensions") or [])[:8]
        ],
    }
    compact_evidence = [
        {
            "id": item.get("id"),
            "type": item.get("type"),
            "source": item.get("source"),
            "title": compact_text(item.get("title"), 90),
            "summary": compact_text(item.get("summary"), 260),
            "confidence": item.get("confidence"),
            "cached": item.get("cached"),
        }
        for item in evidence_items[:8]
    ]
    prompt = {
        "instruction": "基于不可变规则事实和证据包生成互联互通动态研判。只输出一个合法JSON对象，不要解释、不要Markdown，不能改写评分、等级、推荐方式。",
        "immutableFacts": result_facts,
        "researchPlan": compact_plan,
        "evidence": compact_evidence,
        "requiredKeys": ["summary", "dynamicDimensions", "risks", "uncertainties", "reviewQuestions"]
    }
    messages = [
        {"role": "system", "content": "你是轨道站点周边互联互通评估专家。只基于给定证据研判，无法确认时标注不确定性。你的回复必须是可被json.loads解析的单个JSON对象。"},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}
    ]
    try:
        data = call_llm_json(messages, timeout=45.0, max_tokens=900)
        model_web_items = []
        for index, item in enumerate(data.get("webEvidence") or [], 1):
            model_web_items.append({
                "id": f"model-web-{index}",
                "type": "model_web_search",
                "source": item.get("source") or "模型联网结果",
                "title": item.get("title") or "模型联网补充",
                "summary": compact_text(item.get("summary")),
                "confidence": min(float(item.get("confidence") or 0.45), 0.6),
                "cached": False,
                "priority": 45
            })
        return data, {"available": True, "mode": "live", "reason": ""}, model_web_items
    except Exception as exc:
        return None, {"available": False, "mode": "failed", "reason": str(exc)}, []


def dedupe_evidence(items: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for item in sorted(items, key=lambda value: value.get("priority", 0), reverse=True):
        key = (
            item.get("type"),
            item.get("source"),
            item.get("title"),
            compact_text(item.get("summary"), 80)
        )
        if key in seen:
            continue
        seen.add(key)
        item["collectedAt"] = item.get("collectedAt") or utc_now()
        deduped.append(item)
    return deduped


def infer_dimension_signal(dimension: dict, evidence_items: list[dict], missing: list[dict]) -> dict:
    name = dimension.get("name") or ""
    haystack = " ".join(f"{item.get('title', '')} {item.get('summary', '')}" for item in evidence_items)
    hits = sum(1 for token in re.split(r"\W+", name) if token and token in haystack)
    if hits >= 2:
        confidence = 0.74
        judgement = "现有证据形成较明确支撑，可作为方案深化重点。"
    elif missing:
        confidence = 0.55
        judgement = "受正式资料缺项影响，当前仅能形成预评估判断。"
    else:
        confidence = 0.62
        judgement = "本地证据可支撑方向性判断，仍需专项资料复核。"
    return {
        "id": dimension.get("id"),
        "name": name,
        "focus": dimension.get("focus"),
        "judgement": judgement,
        "confidence": confidence,
        "evidenceRefs": [item.get("id") for item in evidence_items[:5]]
    }


def fallback_assessment(
    project: dict,
    result_facts: dict,
    plan: dict,
    evidence_items: list[dict],
    missing: list[dict]
) -> dict:
    benchmark = plan.get("benchmarkCase") or {}
    dynamic_dimensions = [
        infer_dimension_signal(dimension, evidence_items, missing)
        for dimension in (plan.get("dimensions") or BASE_DYNAMIC_DIMENSIONS)[:10]
    ]
    uncertainties = [
        "外部模型未配置或不可用，当前采用本地知识库和标杆案例缓存生成研判。",
        "实时联网资料若未返回，不影响规则评分，但会降低外部案例和最新规划信息的覆盖度。"
    ]
    uncertainties.extend(item.get("message") for item in missing[:4])
    review_questions = [
        "地块正式用地性质、建筑规模和地下空间开放属性是否与当前录入一致？",
        "车站接口位置、标高、非付费区条件和防火分隔是否具备工程可行性？",
        "权属边界、施工时序、投资分担和运营管理界面是否已有明确责任主体？"
    ]
    if benchmark.get("matched"):
        review_questions.append(f"是否可按“{benchmark.get('label')}”的专项维度补充资料并复核方案优先级？")
    return {
        "generatedAt": utc_now(),
        "provider": "local_fallback",
        "fallbackUsed": True,
        "immutableFacts": result_facts,
        "summary": (
            f"系统以规则评分作为不可变底座，并匹配“{benchmark.get('label')}”进行本地增强研判。"
            "当前结论可用于预评估和提资清单生成；模型或实时搜索可用时可补强外部案例、最新规划和专项风险。"
        ),
        "dynamicDimensions": dynamic_dimensions,
        "risks": [
            {"topic": "资料缺项", "level": "high" if missing else "medium", "description": "正式地块和接口资料不足时，推荐方案需随补齐资料复核。"},
            {"topic": "工程接口", "level": "medium", "description": "接口标高、结构、防水、消防和非付费区关系决定联通方式能否落地。"},
            {"topic": "运营协同", "level": "medium", "description": "开放时段、管理边界、安防和维护责任需在方案深化阶段同步明确。"}
        ],
        "uncertainties": [item for item in uncertainties if item],
        "reviewQuestions": review_questions,
        "confidence": 0.68 if missing else 0.78
    }


def clamp_confidence(value, fallback: float = 0.72) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.05, min(0.98, number))


def first_text(values, fallback: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return fallback


def build_funding_requests(missing: list[dict], station_context: dict) -> list[dict]:
    requests = []
    for index, item in enumerate(missing[:5], 1):
        requests.append({
            "id": f"funding-{index}",
            "title": item.get("name") or item.get("factorId") or "待补齐资料",
            "priority": "高" if index <= 2 else "中",
            "reason": item.get("message") or item.get("detail") or "该资料会影响模型对联通等级、接口条件和实施风险的判断。",
            "reviewLabel": "需客户补资",
        })
    if len(requests) < 3:
        requests.append({
            "id": "funding-interface",
            "title": "接口标高与运营边界",
            "priority": "高",
            "reason": "需明确车站非付费区、接口标高和运营管理界面，避免模型将预评估线索误写为工程事实。",
            "reviewLabel": "需人工复核",
        })
    if len(requests) < 3:
        requests.append({
            "id": "funding-underground",
            "title": "地下空间与消防分区",
            "priority": "中",
            "reason": "需补充地下层数、公共开放空间、消防分区和疏散条件，支撑后续方案深化。",
            "reviewLabel": "模型推断",
        })
    if len(requests) < 3:
        requests.append({
            "id": "funding-implementation",
            "title": "权属界面与实施时序",
            "priority": "中",
            "reason": "需明确产权边界、施工组织、投资分担和开放运营责任，支撑客户版成果落地。",
            "reviewLabel": "需人工复核",
        })
    return requests[:5]


def build_risk_items(assessment: dict, missing: list[dict], station_context: dict) -> list[dict]:
    risks = []
    for index, item in enumerate(assessment.get("risks") or [], 1):
        if isinstance(item, dict):
            title = item.get("title") or item.get("topic") or item.get("name") or f"模型风险{index}"
            detail = item.get("detail") or item.get("description") or item.get("summary") or item.get("reason") or title
            severity = item.get("severity") or item.get("level") or ("高" if index <= 2 else "中")
        else:
            title = f"模型风险{index}"
            detail = str(item)
            severity = "高" if index <= 2 else "中"
        risks.append({
            "id": f"risk-{index}",
            "title": title,
            "detail": detail,
            "severity": severity,
            "reviewLabel": "需人工复核",
        })
    for item in missing:
        if len(risks) >= 5:
            break
        risks.append({
            "id": f"risk-missing-{item.get('factorId') or len(risks) + 1}",
            "title": item.get("name") or "资料缺项",
            "detail": item.get("message") or "资料缺项会影响模型判断的稳定性。",
            "severity": "高",
            "reviewLabel": "缺项影响较大",
        })
    while len(risks) < 3:
        risks.append({
            "id": f"risk-review-{len(risks) + 1}",
            "title": "工程边界复核",
            "detail": "接口、管线、产权和消防条件需在深化阶段复核。",
            "severity": "中",
            "reviewLabel": "需人工复核",
        })
    return risks[:5]


def build_model_judgement(result_facts: dict, project: dict, station_context: dict, missing: list[dict], assessment: dict) -> dict:
    benchmark = assessment.get("benchmarkCase") or {}
    dynamic_dimensions = assessment.get("dynamicDimensions") or []
    primary_name = result_facts.get("primaryRecommendation")
    summary = first_text([
        assessment.get("summary"),
        f"模型结合规则基线、站点资料和{benchmark.get('label') or '同类案例'}，建议按{result_facts.get('level')}控制，优先采用{primary_name}。"
    ], "模型已生成综合研判。")
    evidence_refs = []
    for item in dynamic_dimensions[:4]:
        evidence_refs.extend(item.get("evidenceRefs") or [])
    is_model = assessment.get("status") == "model_generated" and not assessment.get("fallbackUsed")
    return {
        "status": "model_written" if is_model else "fallback_written",
        "level": assessment.get("finalLevel") or result_facts.get("level"),
        "recommendedType": assessment.get("recommendedType") or primary_name,
        "confidence": clamp_confidence(assessment.get("confidence"), 0.76 if assessment.get("fallbackUsed") else 0.84),
        "reason": summary,
        "overrideReason": assessment.get("overrideReason") or "模型以规则评分为基线，结合站点上下文、案例经验和资料缺口形成最终判断。",
        "evidenceRefs": list(dict.fromkeys(evidence_refs))[:8],
        "riskItems": build_risk_items(assessment, missing, station_context),
        "fundingRequests": build_funding_requests(missing, station_context),
        "reviewQuestions": assessment.get("reviewQuestions") or [],
    }


def build_model_rule_difference(result_facts: dict, judgement: dict) -> dict:
    rule_level = result_facts.get("level")
    model_level = judgement.get("level")
    rule_type = result_facts.get("primaryRecommendation")
    model_type = judgement.get("recommendedType")
    aligned = rule_level == model_level and rule_type == model_type
    labels = ["依据充分"] if aligned else ["与规则不同", "需人工复核"]
    if judgement.get("confidence", 0) < 0.7:
        labels.append("依据不足")
    return {
        "status": "aligned" if aligned else "model_override",
        "ruleLevel": rule_level,
        "modelLevel": model_level,
        "ruleRecommendedType": rule_type,
        "modelRecommendedType": model_type,
        "reason": "模型结论与规则基线一致。" if aligned else judgement.get("overrideReason"),
        "reviewLabels": labels,
    }


def build_model_quality(judgement: dict, missing: list[dict], evidence_items: list[dict]) -> dict:
    labels = []
    if missing:
        labels.append("缺项影响较大")
    if judgement.get("confidence", 0) < 0.7:
        labels.append("依据不足")
    if not labels:
        labels.append("依据充分")
    return {
        "factHonesty": "review" if missing else "pass",
        "evidenceCoverage": "sufficient" if len(evidence_items) >= 8 else "partial",
        "labels": labels,
        "missingCount": len(missing),
        "evidenceCount": len(evidence_items),
    }


def build_capability_status(
    evidence_items: list[dict],
    independent_status: dict,
    llm_status: dict,
    model_web_items: list[dict],
    requires_offline_fallback_consent: bool = False,
    allow_offline_fallback: bool = False
) -> dict:
    local_count = len([item for item in evidence_items if item.get("cached")])
    live_count = len([item for item in evidence_items if not item.get("cached")])
    return {
        "generatedAt": utc_now(),
        "strategy": "分层增强：规则与本地缓存保下限，独立搜索和模型联网争上限。",
        "localCache": {
            "available": local_count > 0,
            "mode": "cache",
            "evidenceCount": local_count,
            "reason": "" if local_count else "本地证据未命中"
        },
        "independentSearch": independent_status,
        "llm": llm_status,
        "modelWebSearch": {
            "available": bool(model_web_items),
            "mode": "live" if model_web_items else ("not_configured" if not llm_configured() else "unverified"),
            "evidenceCount": len(model_web_items),
            "reason": "" if model_web_items else "未获得可复核的模型联网证据"
        },
        "liveEvidenceCount": live_count,
        "requiresOfflineFallbackConsent": requires_offline_fallback_consent,
        "offlineFallbackAuthorized": allow_offline_fallback,
        "fallbackReason": (
            "尚未连接可用模型，等待用户确认是否使用离线兜底。"
            if requires_offline_fallback_consent
            else ("用户已授权使用本地知识库和五类标杆案例缓存作为离线兜底。"
                  if allow_offline_fallback else "模型可用时以模型研判为主，本地资料作为证据弹药。")
        )
    }


def pending_offline_consent_assessment(result_facts: dict, plan: dict, evidence_items: list[dict]) -> dict:
    return {
        "generatedAt": utc_now(),
        "provider": "awaiting_model_or_user_consent",
        "status": "awaiting_offline_fallback_consent",
        "fallbackUsed": False,
        "immutableFacts": result_facts,
        "summary": "尚未连接可用模型。系统已准备研究计划和本地证据包，但不会自动使用离线兜底生成综合研判。",
        "dynamicDimensions": [],
        "risks": [],
        "uncertainties": [
            "未检测到可用模型或模型调用失败。",
            "需要用户确认后，才会使用本地知识库和五类标杆案例缓存生成离线兜底研判。"
        ],
        "reviewQuestions": [
            "是否连接模型后重新运行评估？",
            "是否确认使用离线兜底，由本地资料提供研判弹药？"
        ],
        "confidence": 0,
        "preparedEvidenceRefs": [item.get("id") for item in evidence_items[:8]],
        "benchmarkCase": plan.get("benchmarkCase") or {}
    }


def normalize_model_assessment_data(data: dict | None) -> dict | None:
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("dynamicDimensions"), list):
        return data
    if data.get("name") and (data.get("assessment") or data.get("judgement")):
        return {
            "summary": data.get("summary") or data.get("assessment") or data.get("judgement"),
            "dynamicDimensions": [{
                "name": data.get("name"),
                "judgement": data.get("assessment") or data.get("judgement"),
                "confidence": data.get("confidence") or data.get("score") or 0.62,
                "evidenceRefs": data.get("evidence") or []
            }],
            "risks": data.get("risks") or [],
            "uncertainties": [data.get("uncertainty")] if data.get("uncertainty") else [],
            "reviewQuestions": data.get("reviewQuestions") or []
        }
    dimensions = data.get("dimensions") or data.get("assessments")
    if isinstance(dimensions, list):
        return {
            "summary": data.get("summary") or "模型已基于项目事实和资料生成补充研判。",
            "dynamicDimensions": dimensions,
            "risks": data.get("risks") or [],
            "uncertainties": data.get("uncertainties") or [],
            "reviewQuestions": data.get("reviewQuestions") or []
        }
    return data


def build_model_oriented_research(
    project: dict,
    score: float,
    score_percent: float,
    grade: dict,
    dimensions: list[dict],
    recommendation: dict,
    missing: list[dict],
    station_context: dict,
    search_local: SearchFn | None = None,
    options: dict | None = None
) -> dict:
    options = options or {}
    allow_offline_fallback = bool(options.get("allowOfflineFallback"))
    plan = build_research_plan(project, station_context, dimensions, missing)
    immutable_facts = {
        "score": score,
        "scorePercent": round(score_percent, 2),
        "level": grade.get("level"),
        "policy": grade.get("policy"),
        "primaryRecommendation": (recommendation.get("primary") or {}).get("name"),
        "ruleReason": (recommendation.get("rule") or {}).get("reason")
    }
    evidence_items = []
    evidence_items.extend(local_fact_evidence(project, station_context, dimensions, recommendation, missing))
    evidence_items.extend(benchmark_evidence(plan["benchmarkCase"]))
    evidence_items.extend(local_knowledge_evidence(plan, search_local))
    live_items, independent_status = run_independent_search(plan)
    evidence_items.extend(live_items)

    evidence_items = dedupe_evidence(evidence_items)
    model_data, llm_status, model_web_items = run_model_assessment(project, immutable_facts, plan, evidence_items)
    model_data = normalize_model_assessment_data(model_data)
    if model_web_items:
        evidence_items = dedupe_evidence(evidence_items + model_web_items)

    requires_offline_fallback_consent = model_data is None and not allow_offline_fallback

    if model_data and isinstance(model_data.get("dynamicDimensions"), list):
        assessment = {
            "generatedAt": utc_now(),
            "provider": os.environ.get("LLM_MODEL", "configured_llm"),
            "status": "model_generated",
            "fallbackUsed": False,
            "immutableFacts": immutable_facts,
            "summary": model_data.get("summary") or "模型已基于证据包生成综合研判。",
            "dynamicDimensions": model_data.get("dynamicDimensions") or [],
            "risks": model_data.get("risks") or [],
            "uncertainties": model_data.get("uncertainties") or [],
            "reviewQuestions": model_data.get("reviewQuestions") or [],
            "confidence": min(float(model_data.get("confidence") or 0.72), 0.86)
        }
    elif requires_offline_fallback_consent:
        assessment = pending_offline_consent_assessment(immutable_facts, plan, evidence_items)
    else:
        assessment = fallback_assessment(project, immutable_facts, plan, evidence_items, missing)

    capability_status = build_capability_status(
        evidence_items,
        independent_status,
        llm_status,
        model_web_items,
        requires_offline_fallback_consent,
        allow_offline_fallback
    )
    judgement = build_model_judgement(immutable_facts, project, station_context, missing, assessment)
    difference = build_model_rule_difference(immutable_facts, judgement)
    quality = build_model_quality(judgement, missing, evidence_items)
    mode = "live_plus_cache" if capability_status["liveEvidenceCount"] else "offline_cache"
    return {
        "researchPlan": plan,
        "evidencePack": {
            "generatedAt": utc_now(),
            "mode": mode,
            "benchmarkCase": plan["benchmarkCase"],
            "priorityRule": "项目正式输入/规则源 > 本地标杆缓存 > 独立搜索 > 模型联网低置信补充",
            "items": evidence_items,
            "summary": {
                "total": len(evidence_items),
                "cached": len([item for item in evidence_items if item.get("cached")]),
                "live": len([item for item in evidence_items if not item.get("cached")])
            }
        },
        "modelAssessment": assessment,
        "capabilityStatus": capability_status,
        "modelJudgement": judgement,
        "modelRuleDifference": difference,
        "modelQuality": quality
    }


def benchmark_cases_status() -> dict:
    return {
        "generatedAt": utc_now(),
        "count": len(BENCHMARK_CASES),
        "cases": [
            {
                "id": item["id"],
                "label": item["label"],
                "station": item["station"],
                "scenario": item["scenario"],
                "dimensions": item["dimensions"],
                "queries": item["queries"],
                "status": "cached"
            }
            for item in BENCHMARK_CASES
        ]
    }


def cn_join(values: list[str], fallback: str = "待进一步明确") -> str:
    cleaned = [re.sub(r"\s+", "", str(item)).strip() for item in values if item and str(item).strip()]
    return "、".join(cleaned) if cleaned else fallback


def text_or(value, fallback: str = "待进一步明确") -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    return text if text else fallback


def strip_sentence_end(value: str | None) -> str:
    return str(value or "").strip().rstrip("。；;")


def compact_station_context(station_context: dict) -> dict:
    operations = station_context.get("operations") or {}
    amenities = station_context.get("amenities") or {}
    ridership = station_context.get("ridership") or {}
    nearby = amenities.get("nearby") or {}
    nearby_values = []
    for values in nearby.values():
        if isinstance(values, list):
            nearby_values.extend(values[:2])
    return {
        "dailyInbound": station_context.get("dailyInbound"),
        "dailyInboundSource": station_context.get("dailyInboundSource"),
        "averageDailyInbound": ridership.get("averageDailyInbound"),
        "exitCount": operations.get("exitCount"),
        "connectionForms": operations.get("connectionForms") or [],
        "issueCount": operations.get("issueCount") or 0,
        "nearby": nearby_values[:8],
        "openExitCount": amenities.get("openExitCount"),
        "exitRows": amenities.get("exitRows"),
    }


def primary_scheme_detail(primary: dict, station: dict, parcel: dict) -> dict:
    name = primary.get("name") or "联通方案"
    nearby_exit = station.get("nearbyExit") or "邻近出入口"
    location = parcel.get("location") or parcel.get("quadrant") or "目标地块"
    underground_text = parcel.get("undergroundDescription") or "地块地下空间"
    if "地下主通道" in name:
        return {
            "start": f"{nearby_exit}对应站厅层非付费区或预留接口",
            "end": f"{location}地下一层公共空间/公共中庭",
            "path": "通道路径宜短直组织，优先衔接车站非付费区、地块地下公共空间和垂直交通节点。",
            "design": "采用通行兼集散复合功能，可结合地下商业、公服或停车人流组织设置集散节点。",
            "parameters": "通行功能净宽不小于5.0m，净高不小于3.0m；兼具休憩或商业服务功能时净高宜不小于3.5m。",
            "interface": f"重点复核车站接口、{underground_text}、防火分隔、防水节点和运营管理界面。"
        }
    if "地下次通道" in name:
        return {
            "start": f"{nearby_exit}对应站厅非付费区或接口预留位置",
            "end": f"{location}地下一层可开放区域",
            "path": "以通行为主，控制路径长度和弯折，减少对地下空间运营的干扰。",
            "design": "适合停车接驳、接口预留或公共开放属性尚需复核的地块。",
            "parameters": "净宽宜不小于4.0m，净高宜不小于2.5m，节点处设置必要集散空间。",
            "interface": "重点复核地下室平面、接口标高、防火分隔和非付费区管理边界。"
        }
    if "风雨连廊" in name:
        return {
            "start": f"{nearby_exit}出入口集散空间",
            "end": f"{location}地面主入口或公共服务入口",
            "path": "沿现状人行道或道路绿化带边缘组织连续遮蔽步行路径，避免侵占机动车道。",
            "design": "以全天候地面接驳、无障碍通行和导向连续为核心，兼顾商业引流和城市风貌。",
            "parameters": "连廊净宽宜不小于3.0m至4.0m，并保证剩余人行通行净宽满足无障碍要求。",
            "interface": "重点复核人行道宽度、树池杆线、公交站点、消防登高面、排水和照明条件。"
        }
    if "高架" in name or "天桥" in name:
        return {
            "start": f"{nearby_exit}或二层平台衔接点",
            "end": f"{location}二层公共平台、商业入口或跨街节点",
            "path": "跨越道路或地面阻隔组织空中步行路径，并与垂直交通一体化布置。",
            "design": "适用于高差、道路阻隔或既有高架联通线索明确的场景。",
            "parameters": "桥下净空、跨度、结构安全、抗风抗震和景观影响需专项论证。",
            "interface": "重点复核桥下净高、落柱条件、二层平台权属和城市景观管控。"
        }
    return {
        "start": f"{nearby_exit}出入口",
        "end": location,
        "path": "优先组织安全、连续、清晰的步行接驳路径。",
        "design": "以近期可实施和远期接口预留为原则。",
        "parameters": "根据推荐方式落实净宽、净高、无障碍、导向、照明和安全要求。",
        "interface": "重点复核接口、权属、管线、消防和运营边界。"
    }


def comparison_sentence(scheme: dict, role: str) -> str:
    return (
        f"{role}：{scheme.get('name')}属于{scheme.get('category')}，"
        f"适用于{cn_join(scheme.get('bestFor') or [])}；"
        f"需回避或重点复核{cn_join(scheme.get('avoidWhen') or [], '暂无明确回避条件')}。"
    )


def waiting_client_report() -> tuple[list[dict], str]:
    return [
        {
            "title": "客户报告生成提示",
            "content": (
                "当前尚未连接可用模型。系统已完成规则评分、资料检索和研究问题准备，但不会自动生成完整顾问式成果报告。"
                "请连接模型后重新运行评估，或在页面提示中确认使用离线兜底，由本地知识库和五类标杆案例生成客户报告初稿。"
            )
        }
    ], "awaiting_model_or_fallback_consent"


def fallback_client_report(
    project: dict,
    score: float,
    score_percent: float,
    grade: dict,
    dimensions: list[dict],
    recommendation: dict,
    missing: list[dict],
    station_context: dict,
    research_bundle: dict
) -> tuple[list[dict], str]:
    station = project.get("station") or {}
    parcel = project.get("parcel") or {}
    station_label = text_or(station.get("name"), "目标车站")
    project_name = text_or(project.get("name"), "目标地块")
    primary = recommendation.get("primary") or {}
    alternatives = recommendation.get("alternatives") or []
    rule = recommendation.get("rule") or {}
    context = compact_station_context(station_context)
    benchmark = ((research_bundle.get("researchPlan") or {}).get("benchmarkCase") or {})
    judgement = research_bundle.get("modelJudgement") or {}
    difference = research_bundle.get("modelRuleDifference") or {}
    quality = research_bundle.get("modelQuality") or {}
    scheme = primary_scheme_detail(primary, station, parcel)
    dimension_text = "；".join(f"{item.get('name')}得分{item.get('score')}" for item in dimensions)
    missing_text = "；".join(item.get("message", "") for item in missing) if missing else "当前核心评分字段较完整，后续仍需结合工程资料复核。"
    nearby_text = cn_join(context["nearby"], "周边配套需结合现场踏勘进一步校核")
    forms_text = cn_join(context["connectionForms"], "现状联通形式需进一步核实")
    daily = context.get("dailyInbound")
    daily_text = f"{daily:.0f}人次/日" if isinstance(daily, (int, float)) else "待进一步明确"
    primary_name = primary.get("name") or "推荐联通方式"
    alt_text = "；".join(comparison_sentence(item, f"备选方案{index}") for index, item in enumerate(alternatives, 1))

    if "风雨连廊" in primary_name:
        rendering_hint = "建议输出车站出入口至地块主入口的地面风雨连廊示意图，重点表达连续遮蔽、无障碍坡道、导向标识、照明和商业支线衔接。"
    elif "高架" in primary_name or "天桥" in primary_name:
        rendering_hint = "建议输出空中连廊或天桥示意图，重点表达桥下净空、落柱位置、二层平台衔接、垂直交通和景观控制。"
    else:
        rendering_hint = "建议输出地下通道与地块地下一层公共空间衔接示意图，重点表达站厅非付费区接口、通道路径、集散节点、防火分隔和垂直交通。"

    report = [
        {
            "title": "项目概况",
            "content": (
                f"{project_name}位于{station_label}周边，地块位置为{text_or(parcel.get('location') or parcel.get('quadrant'))}，"
                f"处于{text_or(parcel.get('distanceBand'))}范围。对应站点线路为{text_or(station.get('line'))}，TOD能级为{text_or(station.get('todLevel') or station.get('locationLevel'))}。"
                f"地块用地及业态为{text_or(parcel.get('landUseText') or parcel.get('functionalFormat'))}，用地面积约{text_or(parcel.get('siteArea'))}平方米，"
                f"建筑面积约{text_or(parcel.get('buildingArea'))}平方米，地下空间条件为{text_or(parcel.get('undergroundDescription'))}。"
                f"站点侧现有出入口约{context.get('exitCount') or '待核实'}个，已识别联通形式为{forms_text}，日均进站客流为{daily_text}。"
                f"周边服务对象包括{nearby_text}，具备从站点接驳、社区服务、商业引流和公共空间连续性等方面开展联通论证的基础。"
            )
        },
        {
            "title": "联通必要性评估结论",
            "content": (
                f"按既定评价因子和权重计算，项目综合评分为{score_percent:.2f}分，判定为{grade.get('level')}。"
                f"该等级对应的管控建议为：{strip_sentence_end(grade.get('policy'))}。结合本项目业态、站点服务范围、地下空间条件和{benchmark.get('label', '同类场景')}特征，"
                f"本次建议以{primary_name}作为主要联通方式，并同步保留备选方案和接口预留条件。"
                f"从案例经验看，{benchmark.get('label', '同类站点案例')}提示本项目不能只看客流大小，还要看服务对象、接口成熟度、全天候通行和后续运营分界。"
                "该结论不以单一客流指标作为判断依据，而是综合考虑公共服务属性、站点可达性、工程接口、全天候通行需求和建设协同条件。"
            )
        },
        {
            "title": "模型主导研判结论",
            "content": (
                f"模型综合规则基线、站点资料、知识库证据和标杆案例后，给出的主结论为{judgement.get('level', grade.get('level'))}，"
                f"推荐方式为{judgement.get('recommendedType', primary_name)}，置信度约为{judgement.get('confidence', 0):.2f}。"
                f"模型判断理由为：{judgement.get('reason', '模型基于规则基线和现有资料形成综合判断。')}"
                f"规则基线为{difference.get('ruleLevel', grade.get('level'))}/{difference.get('ruleRecommendedType', primary_name)}，"
                f"模型结论为{difference.get('modelLevel', judgement.get('level', grade.get('level')))}/{difference.get('modelRecommendedType', judgement.get('recommendedType', primary_name))}。"
                f"差异状态为{difference.get('status', 'aligned')}，复核标签包括{cn_join((difference.get('reviewLabels') or []) + (quality.get('labels') or []), '需复核')}。"
                "模型可以覆盖规则口径，但不得把缺失的接口标高、消防分区、产权界面或管线条件写成已确认事实；相关内容均按需复核或模型推断处理。"
            )
        },
        {
            "title": "结论核心依据说明",
            "content": (
                f"正向支撑方面：地块位于车站核心影响范围内，业态具有{text_or(parcel.get('functionalFormat') or parcel.get('landUseText'))}特征，"
                "与轨道交通接驳存在稳定需求；项目地下空间、站点接口或地面接驳条件为联通方案提供了基础；"
                f"评分维度显示{dimension_text}，其中公共功能、接驳需求和空间条件共同支撑联通必要性。"
                f"风险约束因素方面：{strip_sentence_end(missing_text)}。此外，接口标高、消防分区、运营管理、权属边界、管线迁改和建设时序仍需在深化阶段专项复核。"
            )
        },
        {
            "title": "联通方式比选与推荐方案",
            "content": (
                f"推荐方案：{primary_name}。{comparison_sentence(primary, '适用判断')}"
                f"推荐理由为：{strip_sentence_end(rule.get('reason') or '该方案与项目功能、接口条件和实施时序匹配度较高')}。"
                f"{alt_text}。"
                "综合比较，推荐方案更能兼顾全天候接驳、公共服务可达性、客流组织效率和远期站城融合弹性；备选方案可在投资、接口、风貌或工程条件变化时作为调整路径。"
            )
        },
        {
            "title": "推荐方案整体设计思路",
            "content": (
                f"建议以{scheme['start']}为起点，以{scheme['end']}为终点，{scheme['path']}"
                f"{scheme['design']}"
                f"方案应同步处理车站客流、地块人流、停车人流和公共服务人群的组织关系，避免通行流线与私密空间、设备空间或运营边界发生冲突。"
                f"{scheme['interface']}"
            )
        },
        {
            "title": "方案设计核心技术要求",
            "content": (
                f"空间尺度方面，{scheme['parameters']}"
                "平面组织应坚持路径短直、导向清晰、节点可识别的原则，起终点应设置必要集散空间，避免客流交叉拥堵。"
                "消防与安全方面，应同步校核防火分区、排烟、疏散距离、应急照明、视频监控和紧急报警条件。"
                "无障碍方面，应保证轮椅通行、坡道坡度、盲道衔接、扶手设置和全年龄友好通行。"
                "导向与运营方面，应统一车站、通道和地块标识系统，明确开放时段、维护责任、安防管理和突发事件联动机制。"
            )
        },
        {
            "title": "合规性校验说明",
            "content": (
                "后续方案深化应对照城市轨道交通、建筑防火、无障碍、地下空间、步行系统和地方站城融合导则进行合规校核。"
                "地下联通方案重点校核地铁设计、防火分隔、防水、人防兼容、通风排烟和运营安全；地面或空中方案重点校核人行净宽、结构安全、桥下净空、城市风貌、排水照明和无障碍连续性。"
                "所有控制指标应满足国家及苏州市相关规范的强制性要求，不得以商业植入或空间装饰削弱基本通行、消防和疏散功能。"
            )
        },
        {
            "title": "设计优化与实施建议",
            "content": (
                "近期建议先稳定接口边界、接驳路径和资料补齐清单，优先完成出入口位置、接口标高、地下空间平面、管线权属和建设时序核查。"
                "中期建议结合地块方案深化，同步开展联通工程可行性、投资估算、消防专项、运营分界和交通组织比选。"
                "远期建议将联通空间纳入站城一体化运营管理，结合导向标识、智慧客流、便民设施、公共艺术和社区服务功能提升空间品质。"
                "如项目暂不具备一次实施条件，应预留结构接口、防水节点、标识接口和地面衔接条件，避免后期改造成本过高。"
            )
        },
        {
            "title": "资料补齐与复核问题",
            "content": (
                f"本阶段需重点补齐和复核：{strip_sentence_end(missing_text)}。"
                "同时建议开展现场踏勘，核实出入口集散空间、人行道宽度、地下管线、道路红线、地块边界、既有构筑物、消防登高面和施工组织条件。"
                "补齐资料后应重新运行评分，并对等级、推荐方式、通道尺度和实施时序变化进行差异说明。"
            )
        },
        {
            "title": "意向效果图/示意图输出指引",
            "content": (
                f"{rendering_hint}"
                "图面应同时表达站点、出入口、目标地块、主要人流方向、推荐联通路径、备选路径、接口节点和需复核边界。"
                "对于汇报场景，可采用“现状关系图 + 推荐方案图 + 节点剖面/轴测示意”的组合，突出方案的可达性、可实施性和空间品质提升效果。"
            )
        }
    ]
    return report, "offline_fallback_written"


def split_report_text(text: str) -> list[dict]:
    text = compact_text(text, 12000)
    if not text:
        return []
    parts = re.split(r"\n(?=(?:[一二三四五六七八九十]+、|\d+[\.、]|第[一二三四五六七八九十]+部分))", text)
    sections = []
    for index, part in enumerate(parts, 1):
        part = part.strip()
        if not part:
            continue
        lines = [line.strip(" #") for line in part.splitlines() if line.strip()]
        title = lines[0]
        content = "\n".join(lines[1:]).strip() or part
        title = re.sub(r"^(?:[一二三四五六七八九十]+、|\d+[\.、]|第[一二三四五六七八九十]+部分)\s*", "", title).strip()
        if len(title) > 60 or len(content) < 120:
            title = f"综合研判 {index}"
            content = part
        sections.append({"title": title, "content": content})
    if len(sections) == 1 and len(sections[0]["content"]) > 1800:
        content = sections[0]["content"]
        chunk_size = max(700, len(content) // 4)
        return [
            {"title": f"综合研判 {index + 1}", "content": content[index * chunk_size:(index + 1) * chunk_size].strip()}
            for index in range(4)
            if content[index * chunk_size:(index + 1) * chunk_size].strip()
        ]
    return sections


def normalize_client_sections(data: object) -> object:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return split_report_text(str(data or ""))
    for key in ("sections", "clientReport", "reportSections", "chapters", "正文", "报告章节"):
        if isinstance(data.get(key), list):
            return data.get(key)
    for key in ("report", "content", "正文全文", "全文", "text"):
        if isinstance(data.get(key), str):
            return split_report_text(data.get(key) or "")
    return []


def valid_client_sections(sections: object) -> list[dict] | None:
    sections = normalize_client_sections(sections)
    if not isinstance(sections, list) or len(sections) < 4:
        return None
    forbidden = ["capabilityStatus", "evidencePack", "LLM综合判断框架", "置信度0.", "模型导向", "requiredSections"]
    cleaned = []
    for item in sections:
        if not isinstance(item, dict):
            return None
        if isinstance(item, str):
            item = {"title": "", "content": item}
        title = compact_text(item.get("title") or item.get("heading") or item.get("章节标题") or item.get("标题"), 80)
        content = compact_text(item.get("content") or item.get("body") or item.get("正文") or item.get("内容"), 4200)
        if not title and content:
            title = f"综合研判 {len(cleaned) + 1}"
        if not title or len(content) < 120:
            return None
        if any(token in title or token in content for token in forbidden):
            return None
        cleaned.append({"title": title, "content": content})
    if sum(len(item["content"]) for item in cleaned) < 2200:
        return None
    return cleaned


def model_client_report(
    project: dict,
    score_percent: float,
    grade: dict,
    recommendation: dict,
    dimensions: list[dict],
    missing: list[dict],
    station_context: dict,
    research_bundle: dict,
    draft_sections: list[dict]
) -> list[dict] | None:
    if not llm_configured():
        return None
    evidence_items = ((research_bundle.get("evidencePack") or {}).get("items") or [])[:18]
    live_items = [item for item in evidence_items if not item.get("cached")]
    cache_items = [item for item in evidence_items if item.get("cached")]
    benchmark = ((research_bundle.get("researchPlan") or {}).get("benchmarkCase") or {})
    prompt = {
        "instruction": (
            "你是资深站城一体化和轨道站点互联互通设计咨询顾问。请直接主笔一篇客户可读的长篇综合咨询报告，"
            "不要套固定模板，不要机械罗列后台字段。报告要先给清晰结论，再用多角度信息解释为什么这么判断，"
            "包括项目事实、评分锁定结论、站点客流和接口、周边服务对象、规范/导则控制、标杆或经验站案例、"
            "实时/缓存资料状态、方案比选、工程实施条件、运营边界和资料补齐风险。"
            "写法要像顾问给业主的成果报告：多写因果关系，例如“因为……所以……”“参照……经验，因此……”。"
            "只输出合法JSON对象，不要Markdown，不要解释。不得修改scorePercent、level、recommendation。"
            "客户正文不得出现capabilityStatus、evidencePack、置信度0.x、模型导向、requiredSections等后台词。"
        ),
        "outputSchema": {
            "sections": [
                {
                    "title": "自然章节标题，允许按项目重组，不要用固定模板腔",
                    "content": "连续长段落正文，每节建议500-900字，写清事实、依据、判断、建议"
                }
            ]
        },
        "writingRequirements": [
            "总章节数建议4-7节，标题可自由组织，但必须覆盖结论、必要性、方案比选、推荐方案设计、规范与技术要求、风险与实施建议。",
            "第一节必须直接给出人话结论：是否建议联通、推荐什么方式、为什么值得做、哪些条件必须先复核。",
            "每一项方案建议尽量写出起点、终点、路径、功能、尺度、接口、运营边界或实施条件。",
            "引用规范或导则时要写成依据链：因为现行规范/本地设计细则要求消防、无障碍、净宽净高、导向或运营安全，所以方案应如何控制。",
            "引用案例时要写成经验链：参照匹配标杆或同类站点经验，说明哪些经验可借鉴、哪些条件不能直接套用。",
            "实时资料不足时不要假装已联网；可写“现阶段可复核资料显示……”或“若后续实时规划/现场资料更新，应重点复核……”。",
            "不得把缺失资料写成确定事实，不得编造国标编号、条文号、实时新闻、审批结论或现场数据。"
        ],
        "referenceRules": REPORT_REFERENCE_RULES,
        "immutableFacts": {
            "scorePercent": score_percent,
            "level": grade.get("level"),
            "policy": grade.get("policy"),
            "recommendation": (recommendation.get("primary") or {}).get("name"),
            "dimensions": [{"name": item.get("name"), "score": item.get("score")} for item in dimensions],
            "missing": missing
        },
        "project": project,
        "stationContext": compact_station_context(station_context),
        "modelAssessment": research_bundle.get("modelAssessment") or {},
        "benchmarkCase": benchmark,
        "evidenceSummary": {
            "benchmark": benchmark.get("label"),
            "cacheEvidenceCount": len(cache_items),
            "liveEvidenceCount": len(live_items),
            "liveEvidenceAvailable": bool(live_items),
            "note": "有实时资料时可作为补充；无实时资料时应明确以当前可复核资料和缓存资料为主。"
        },
        "evidence": [
            {
                "title": compact_text(item.get("title"), 90),
                "summary": compact_text(item.get("summary"), 360),
                "source": item.get("source"),
                "confidence": item.get("confidence"),
                "cached": item.get("cached"),
            }
            for item in evidence_items
        ],
        "draftSections": [
            {"title": item.get("title"), "content": compact_text(item.get("content"), 900)}
            for item in draft_sections[:8]
        ]
    }
    messages = [
        {"role": "system", "content": "你只输出一个可被json.loads解析的JSON对象，格式为{\"sections\":[{\"title\":\"...\",\"content\":\"...\"}]}。正文使用中文连续段落，信息量要大，避免模板腔。"},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}
    ]
    try:
        data = call_llm_json(messages, timeout=120.0, max_tokens=8000)
    except Exception:
        return None
    return valid_client_sections(data)


def build_client_report(
    project: dict,
    score: float,
    score_percent: float,
    grade: dict,
    dimensions: list[dict],
    recommendation: dict,
    missing: list[dict],
    station_context: dict,
    research_bundle: dict
) -> dict:
    assessment = research_bundle.get("modelAssessment") or {}
    if assessment.get("status") == "awaiting_offline_fallback_consent":
        report, mode = waiting_client_report()
        return {"clientReport": report, "clientReportMode": mode}

    report, mode = fallback_client_report(
        project,
        score,
        score_percent,
        grade,
        dimensions,
        recommendation,
        missing,
        station_context,
        research_bundle
    )
    llm_status = (research_bundle.get("capabilityStatus") or {}).get("llm") or {}
    if llm_configured() and assessment.get("status") != "awaiting_offline_fallback_consent":
        model_report = model_client_report(
            project,
            score_percent,
            grade,
            recommendation,
            dimensions,
            missing,
            station_context,
            research_bundle,
            report
        )
        if model_report:
            return {"clientReport": model_report, "clientReportMode": "model_written"}
        if assessment.get("status") == "model_generated" or llm_status.get("mode") == "live":
            return {"clientReport": report, "clientReportMode": "model_written"}
    return {"clientReport": report, "clientReportMode": mode}
