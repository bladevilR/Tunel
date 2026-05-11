import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.server import evaluate_project  # noqa: E402


FORBIDDEN_TERMS = [
    "capabilityStatus",
    "evidencePack",
    "LLM综合判断框架",
    "置信度0.",
    "模型导向",
    "智能研究计划",
    "证据包",
    "requiredSections",
]

REQUIRED_COVERAGE = ["结论", "方案", "规范", "案例", "风险", "实施"]


def assert_true(condition, message, detail=None):
    if not condition:
        raise AssertionError(json.dumps({
            "message": message,
            "detail": detail,
        }, ensure_ascii=False, indent=2))


def demo(case_id):
    payload = json.loads((ROOT / "data" / "demo_cases.json").read_text(encoding="utf-8"))
    return next(item for item in payload["cases"] if item["id"] == case_id)


def client_text(result):
    return "\n".join(f"{item.get('title', '')}\n{item.get('content', '')}" for item in result.get("clientReport") or [])


def check_awaiting_consent():
    result = evaluate_project(demo("jinjiayan-neighborhood-center"))
    assert_true(result.get("clientReportMode") == "awaiting_model_or_fallback_consent", "未接模型且未授权时不得生成正式客户报告", result.get("clientReportMode"))
    report = result.get("clientReport") or []
    assert_true(len(report) <= 3, "未授权离线兜底时客户报告只能给提示，不得输出完整顾问报告", report)
    text = client_text(result)
    assert_true("连接模型" in text or "确认离线兜底" in text, "等待状态必须提示连接模型或确认离线兜底", text)


def check_consultant_report(case_id, required_terms):
    result = evaluate_project(demo(case_id), {"allowOfflineFallback": True})
    report = result.get("clientReport") or []
    text = client_text(result)

    assert_true(result.get("clientReportMode") == "offline_fallback_written", "授权离线兜底后应生成客户报告", result.get("clientReportMode"))
    assert_true(len(report) >= 4, "客户报告不能少于4个综合章节", [item.get("title") for item in report])
    assert_true(len(text) >= 2200, "客户报告正文信息量不足", len(text))
    for term in FORBIDDEN_TERMS:
        assert_true(term not in text, f"客户正文出现后台工程词：{term}", text[:1200])
    for term in REQUIRED_COVERAGE:
        assert_true(term in text, f"客户报告缺少综合覆盖维度：{term}", text[:1600])
    for term in required_terms:
        assert_true(term in text, f"客户报告缺少关键顾问表达：{term}", text[:1600])
    assert_true(not re.search(r"置信度\s*[:：]?\s*0\.", text), "客户正文不得出现小数置信度", text[:1200])


def main():
    check_awaiting_consent()
    check_consultant_report("jinjiayan-neighborhood-center", ["地下主通道", "接口", "净宽", "净高", "消防", "无障碍", "导向", "运营"])
    check_consultant_report("qingshuwan-youth-apartment", ["风雨连廊", "地面接驳", "无障碍", "实施", "导向"])
    print(json.dumps({"ok": True, "checked": ["awaiting_consent", "jinjiayan", "qingshuwan"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
