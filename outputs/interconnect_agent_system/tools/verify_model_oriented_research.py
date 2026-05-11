import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import evaluate_project  # noqa: E402


PROJECTS_PATH = ROOT / "data" / "projects.json"
DEMOS_PATH = ROOT / "data" / "demo_cases.json"


EXPECTED_CASES = {
    "jinjiayan-neighborhood-center": "地下联通商业公服标杆",
    "qingshuwan-youth-apartment": "地面/风雨连廊社区居住标杆",
    "station-乐桥": "城市级换乘高客流标杆",
    "station-阳澄湖中路": "高架天桥联通标杆",
    "station-高铁苏州北站": "交通枢纽站城融合标杆",
}


def load_projects_by_id():
    payload = json.loads(PROJECTS_PATH.read_text(encoding="utf-8"))
    records = {item["id"]: item["project"] for item in payload.get("projects", [])}
    demos = json.loads(DEMOS_PATH.read_text(encoding="utf-8"))
    records.update({item["id"]: item for item in demos.get("cases", [])})
    return records


def assert_true(condition, message, detail=None):
    if not condition:
        raise AssertionError(json.dumps({
            "message": message,
            "detail": detail,
        }, ensure_ascii=False, indent=2))


def check_requires_consent(case_id, project):
    result = evaluate_project(project)
    assessment = result.get("modelAssessment") or {}
    capabilities = result.get("capabilityStatus") or {}
    assert_true(capabilities.get("requiresOfflineFallbackConsent") is True, "未接模型时必须要求用户确认离线兜底", {
        "caseId": case_id,
        "capabilityStatus": capabilities,
    })
    assert_true(assessment.get("status") == "awaiting_offline_fallback_consent", "默认不得自动生成离线兜底研判", {
        "caseId": case_id,
        "modelAssessment": assessment,
    })
    assert_true(assessment.get("fallbackUsed") is False, "默认离线兜底不得自动启用", assessment)


def check_case(case_id, project):
    result = evaluate_project(project, {"allowOfflineFallback": True})
    for key in ("researchPlan", "evidencePack", "modelAssessment", "capabilityStatus"):
        assert_true(key in result, f"评估结果缺少 {key}", {"caseId": case_id, "keys": list(result.keys())})

    plan = result["researchPlan"]
    evidence = result["evidencePack"]
    assessment = result["modelAssessment"]
    capabilities = result["capabilityStatus"]

    assert_true(len(plan.get("questions", [])) >= 5, "研究问题数量不足", {"caseId": case_id, "researchPlan": plan})
    assert_true(len(plan.get("dimensions", [])) >= 6, "动态研判维度数量不足", {"caseId": case_id, "researchPlan": plan})
    assert_true(len(evidence.get("items", [])) >= 8, "证据包条目不足", {"caseId": case_id, "evidencePack": evidence})
    assert_true(evidence.get("mode") in {"live_plus_cache", "cache_only", "offline_cache"}, "证据模式未标注", evidence)
    assert_true("benchmarkCase" in evidence, "证据包缺少标杆案例匹配", evidence)
    assert_true(len(assessment.get("dynamicDimensions", [])) >= 6, "模型/本地研判维度不足", assessment)
    assert_true(assessment.get("fallbackUsed") is True, "授权后应使用本地兜底研判", assessment)
    assert_true(capabilities.get("requiresOfflineFallbackConsent") is False, "授权后不应继续要求离线兜底确认", capabilities)
    assert_true(capabilities.get("localCache", {}).get("available") is True, "本地缓存能力应可用", capabilities)
    assert_true("llm" in capabilities and "independentSearch" in capabilities and "modelWebSearch" in capabilities, "能力状态不完整", capabilities)

    immutable = assessment.get("immutableFacts", {})
    assert_true(immutable.get("score") == result.get("score"), "模型研判不得改写评分", immutable)
    assert_true(immutable.get("level") == result.get("level"), "模型研判不得改写等级", immutable)


def main():
    records = load_projects_by_id()
    missing = [case_id for case_id in EXPECTED_CASES if case_id not in records]
    assert_true(not missing, "五类标杆案例缺失", {"missing": missing, "available": list(records)[:20]})

    first_case_id = next(iter(EXPECTED_CASES))
    check_requires_consent(first_case_id, records[first_case_id])

    for case_id in EXPECTED_CASES:
        check_case(case_id, records[case_id])

    print(json.dumps({
        "ok": True,
        "checkedCases": EXPECTED_CASES,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
