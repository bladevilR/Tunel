from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_FILES = [
    ROOT / "frontend" / "index.html",
    ROOT / "frontend" / "assets" / "app.js",
]

FORBIDDEN_CUSTOMER_COPY = [
    "PPT",
    "规则优先级",
    "PPT规则",
    "评分规则",
    "规则追溯",
    "资料源清单",
    "知识库补齐项",
    "知识库解析缺口",
    "资料就绪度",
    "补齐项总表",
    "待检查",
    "规则卡",
    "source_manifest",
    "后端 exports",
    "交付物",
    "智能研究状态",
    "辅助研究状态",
    "证据包",
    "模型导向",
    "后台",
    "内部",
]


def main() -> int:
    violations = []
    for path in FRONTEND_FILES:
        text = path.read_text(encoding="utf-8")
        for term in FORBIDDEN_CUSTOMER_COPY:
            if term in text:
                violations.append(f"{path.relative_to(ROOT)} contains {term!r}")

    if violations:
        raise SystemExit("\n".join(violations))

    print({"ok": True, "checked": [str(path.relative_to(ROOT)) for path in FRONTEND_FILES]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
