import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import evaluate_project  # noqa: E402


DEMO_PATH = ROOT / "data" / "demo_cases.json"


def assert_true(condition, message, detail=None):
    if not condition:
        raise AssertionError(json.dumps({
            "message": message,
            "detail": detail,
        }, ensure_ascii=False, indent=2))


def first_demo():
    return json.loads(DEMO_PATH.read_text(encoding="utf-8"))["cases"][0]


def main():
    result = evaluate_project(first_demo(), {"allowOfflineFallback": True})
    judgement = result.get("modelJudgement") or {}
    diff = result.get("modelRuleDifference") or {}
    quality = result.get("modelQuality") or {}
    diagram = result.get("diagramBrief") or {}

    assert_true(judgement.get("status") in {"model_written", "fallback_written"}, "模型主导结论状态缺失", judgement)
    assert_true(judgement.get("level"), "模型主导结论必须给出联通等级", judgement)
    assert_true(judgement.get("recommendedType"), "模型主导结论必须给出推荐方式", judgement)
    assert_true(isinstance(judgement.get("confidence"), (int, float)), "模型主导结论必须给出置信度", judgement)
    assert_true(judgement.get("reason"), "模型主导结论必须给出判断理由", judgement)
    assert_true(len(judgement.get("riskItems") or []) >= 3, "模型主导结论必须给出风险项", judgement)
    assert_true(len(judgement.get("fundingRequests") or []) >= 3, "模型主导结论必须给出补资优先级", judgement)

    assert_true(diff.get("ruleLevel") == result.get("level"), "差异检查器必须保留规则等级基线", diff)
    assert_true(diff.get("modelLevel") == judgement.get("level"), "差异检查器必须保留模型等级", diff)
    assert_true(diff.get("ruleRecommendedType") == result.get("recommendation", {}).get("primary", {}).get("name"), "差异检查器必须保留规则推荐方式", diff)
    assert_true(diff.get("modelRecommendedType") == judgement.get("recommendedType"), "差异检查器必须保留模型推荐方式", diff)
    assert_true(diff.get("status") in {"aligned", "model_override"}, "差异检查器状态不正确", diff)
    assert_true(len(diff.get("reviewLabels") or []) >= 1, "差异检查器必须给出复核标签", diff)

    assert_true(quality.get("factHonesty") in {"pass", "review"}, "质量检查器必须标注事实诚实性", quality)
    assert_true(quality.get("evidenceCoverage") in {"sufficient", "partial"}, "质量检查器必须标注依据覆盖", quality)
    assert_true(isinstance(quality.get("labels"), list), "质量检查器必须输出标签数组", quality)

    assert_true(diagram.get("diagramType") == "recommended_connection_path", "一期必须默认生成推荐联通路径图 brief", diagram)
    assert_true(len(diagram.get("nodes") or []) >= 2, "示意图 brief 必须包含节点", diagram)
    assert_true(len(diagram.get("edges") or []) >= 1, "示意图 brief 必须包含路径", diagram)

    modes = result.get("reportModes") or []
    mode_ids = {item.get("id") for item in modes}
    assert_true({"client_formal", "expert_appendix", "leadership_brief"}.issubset(mode_ids), "三类报告模式缺失", modes)

    report_sections = result.get("clientReport") or result.get("report") or []
    joined_report = "\n".join(f"{item.get('title', '')}\n{item.get('content', '')}" for item in report_sections)
    assert_true("模型" in joined_report, "报告正文必须体现模型主导研判", joined_report[:500])
    assert_true("需复核" in joined_report or "模型推断" in joined_report, "报告正文必须体现复核标签", joined_report[:500])

    snapshot_keys = {"modelJudgement", "modelRuleDifference", "modelQuality", "diagramBrief", "reportModes"}
    assert_true(snapshot_keys.issubset(result.keys()), "导出快照所需模型主导字段缺失", sorted(result.keys()))

    print(json.dumps({
        "ok": True,
        "modelJudgement": judgement,
        "difference": diff,
        "quality": quality,
        "diagramBrief": diagram,
        "reportModes": modes,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
