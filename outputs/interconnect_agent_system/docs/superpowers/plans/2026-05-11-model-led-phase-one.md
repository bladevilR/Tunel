# Model-Led Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing interconnect MVP into a model-led phase-one delivery system where the model can override rule conclusions with reasons, confidence, evidence, and review labels.

**Architecture:** Keep the existing Python standard-library backend and native HTML/CSS/JavaScript frontend. Add a model-led assessment contract around the current `research_agent` flow: rules become a baseline, model output becomes the primary judgement, and a difference checker explains where the model agrees with or overrides rules.

**Tech Stack:** Python 3 standard library backend, existing `python-docx` export helpers, native browser JavaScript, Playwright verification scripts, existing PowerShell launcher.

---

## File Structure

- Modify `backend/research_agent.py`: normalize model/fallback assessment into a final judgement object, allow model-led overrides, and add quality/difference labels.
- Modify `backend/server.py`: expose model-led judgement fields in `/api/evaluate`, update report context and generated report language, and include diagram brief data in exports.
- Modify `docs/llm_integration_contract.md`: replace the old “LLM cannot change score/level/recommendation” contract with the approved model-led contract.
- Modify `frontend/index.html`: add containers and controls for model judgement, difference review, report mode tabs, and SVG brief preview.
- Modify `frontend/assets/app.js`: render model-led judgement first on the dashboard, render difference/quality labels in implementation views, switch report modes, and render diagram brief SVG.
- Modify `frontend/assets/styles.css`: style the model-led dashboard, difference checker, report mode tabs, and SVG preview.
- Modify `tools/verify_model_oriented_research.py`: replace old immutable judgement assertions with model-led override assertions.
- Create `tools/verify_model_led_phase_one.py`: backend contract test for final judgement, difference labels, report modes, and diagram brief.
- Create `tools/verify_model_led_ui.cjs`: browser test for customer dashboard, difference checker, report mode tabs, and SVG preview.
- Modify `README.md` and `docs/api_reference.md`: document model-led mode, fallback behavior, and verification commands.

## Task 1: Backend Model-Led Contract

**Files:**
- Modify: `backend/research_agent.py`
- Test: `tools/verify_model_led_phase_one.py`

- [ ] **Step 1: Write the failing backend contract test**

Create `tools/verify_model_led_phase_one.py` with this content:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python .\tools\verify_model_led_phase_one.py
```

Expected: FAIL because `modelJudgement`, `modelRuleDifference`, `modelQuality`, `diagramBrief`, or `reportModes` are not present.

- [ ] **Step 3: Implement normalized model-led objects**

In `backend/research_agent.py`, add helper functions near `build_model_oriented_research`:

```python
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
    return requests[:5]


def build_risk_items(assessment: dict, missing: list[dict], station_context: dict) -> list[dict]:
    risks = []
    for index, item in enumerate(assessment.get("risks") or [], 1):
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or f"模型风险{index}"
            detail = item.get("detail") or item.get("summary") or item.get("reason") or title
        else:
            title = f"模型风险{index}"
            detail = str(item)
        risks.append({
            "id": f"risk-{index}",
            "title": title,
            "detail": detail,
            "severity": "高" if index <= 2 else "中",
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
    recommendation = result_facts.get("recommendation") or {}
    primary = recommendation.get("primary") or {}
    benchmark = assessment.get("benchmarkCase") or {}
    dynamic_dimensions = assessment.get("dynamicDimensions") or []
    summary = first_text([
        assessment.get("summary"),
        f"模型结合规则基线、站点资料和{benchmark.get('label') or '同类案例'}，建议按{result_facts.get('level')}控制，优先采用{primary.get('name')}。"
    ], "模型已生成综合研判。")
    evidence_refs = []
    for item in dynamic_dimensions[:4]:
        evidence_refs.extend(item.get("evidenceRefs") or [])
    return {
        "status": "model_written" if assessment.get("source") == "llm" else "fallback_written",
        "level": assessment.get("finalLevel") or result_facts.get("level"),
        "recommendedType": assessment.get("recommendedType") or primary.get("name"),
        "confidence": clamp_confidence(assessment.get("confidence"), 0.76 if assessment.get("fallbackUsed") else 0.84),
        "reason": summary,
        "overrideReason": assessment.get("overrideReason") or "模型以规则评分为基线，结合站点上下文、案例经验和资料缺口形成最终判断。",
        "evidenceRefs": list(dict.fromkeys(evidence_refs))[:8],
        "riskItems": build_risk_items(assessment, missing, station_context),
        "fundingRequests": build_funding_requests(missing, station_context),
        "reviewQuestions": assessment.get("reviewQuestions") or [],
    }


def build_model_rule_difference(result_facts: dict, judgement: dict) -> dict:
    recommendation = result_facts.get("recommendation") or {}
    primary = recommendation.get("primary") or {}
    rule_level = result_facts.get("level")
    model_level = judgement.get("level")
    rule_type = primary.get("name")
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
```

Then in `build_model_oriented_research`, after `assessment` and `capability_status` are built, compute:

```python
    judgement = build_model_judgement(immutable_facts, project, station_context, missing, assessment)
    difference = build_model_rule_difference(immutable_facts, judgement)
    quality = build_model_quality(judgement, missing, evidence_items)
```

And add these keys to the returned dict:

```python
        "modelJudgement": judgement,
        "modelRuleDifference": difference,
        "modelQuality": quality,
```

- [ ] **Step 4: Run the test to verify partial progress**

Run:

```powershell
python .\tools\verify_model_led_phase_one.py
```

Expected: FAIL only on `diagramBrief` and `reportModes`, because those are implemented in the next task.

## Task 2: Report Modes and Diagram Brief

**Files:**
- Modify: `backend/server.py`
- Test: `tools/verify_model_led_phase_one.py`

- [ ] **Step 1: Add failing expectations for report content**

Update `tools/verify_model_led_phase_one.py` inside `main()` after `modes = result.get("reportModes") or []`:

```python
    report_sections = result.get("clientReport") or result.get("report") or []
    joined_report = "\n".join(f"{item.get('title', '')}\n{item.get('content', '')}" for item in report_sections)
    assert_true("模型" in joined_report, "报告正文必须体现模型主导研判", joined_report[:500])
    assert_true("需复核" in joined_report or "模型推断" in joined_report, "报告正文必须体现复核标签", joined_report[:500])
```

- [ ] **Step 2: Run the test to verify it still fails**

Run:

```powershell
python .\tools\verify_model_led_phase_one.py
```

Expected: FAIL on missing `diagramBrief` / `reportModes` / report language.

- [ ] **Step 3: Add diagram and report mode helpers**

In `backend/server.py`, add these helpers after `build_scheme_comparison`:

```python
def build_diagram_brief(project: dict, result_facts: dict, judgement: dict) -> dict:
    station = (project.get("station") or {}).get("name") or "轨道站点"
    parcel = (project.get("parcel") or {}).get("name") or project.get("name") or "目标地块"
    scheme = judgement.get("recommendedType") or ((result_facts.get("recommendation") or {}).get("primary") or {}).get("name") or "推荐联通方式"
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
```

- [ ] **Step 4: Attach model-led fields in `evaluate_project`**

In `evaluate_project`, after `research_bundle = build_model_oriented_research(...)`, read the new fields:

```python
    model_judgement = research_bundle.get("modelJudgement") or {}
    model_rule_difference = research_bundle.get("modelRuleDifference") or {}
    model_quality = research_bundle.get("modelQuality") or {}
    diagram_brief = build_diagram_brief(project, {
        "level": grade["level"],
        "recommendation": recommendation,
    }, model_judgement)
    report_modes = build_report_modes(model_judgement, model_rule_difference, model_quality)
```

Then include these keys in the returned result:

```python
        "modelJudgement": model_judgement,
        "modelRuleDifference": model_rule_difference,
        "modelQuality": model_quality,
        "diagramBrief": diagram_brief,
        "reportModes": report_modes,
```

- [ ] **Step 5: Update report language**

In `build_report`, update the “LLM综合判断框架” section text so it says:

```python
"模型可以在明确说明理由、证据和复核标签的前提下覆盖规则等级或推荐方案；规则评分作为基线和差异检查坐标保留。"
```

Also add a new report section before the old LLM framework section:

```python
        {
            "title": "模型主导综合研判",
            "content": (
                f"模型主结论为：{model_judgement.get('level', level)}，推荐方式为"
                f"{model_judgement.get('recommendedType', primary.get('name'))}。"
                f"置信度约为{model_judgement.get('confidence', 0):.2f}。"
                f"判断理由：{model_judgement.get('reason', '模型基于规则基线、站点上下文和资料证据形成综合判断。')}"
                f"差异状态：{model_rule_difference.get('status', 'aligned')}；"
                f"复核标签：{join_cn(model_rule_difference.get('reviewLabels') or [])}。"
            )
        },
```

Before adding the section, define:

```python
    model_judgement = research_bundle.get("modelJudgement") or {}
    model_rule_difference = research_bundle.get("modelRuleDifference") or {}
```

- [ ] **Step 6: Run backend test to green**

Run:

```powershell
python .\tools\verify_model_led_phase_one.py
```

Expected: PASS with JSON containing `ok: true`.

- [ ] **Step 7: Commit backend contract**

Run:

```powershell
git add backend/research_agent.py backend/server.py tools/verify_model_led_phase_one.py
git commit -m "feat: add model-led assessment contract"
```

Expected: commit succeeds.

## Task 3: Replace Old Immutable LLM Contract

**Files:**
- Modify: `docs/llm_integration_contract.md`
- Modify: `tools/verify_model_oriented_research.py`
- Test: `tools/verify_model_oriented_research.py`, `tools/verify_model_led_phase_one.py`

- [ ] **Step 1: Write failing assertions for the new contract**

In `tools/verify_model_oriented_research.py`, replace:

```python
    immutable = assessment.get("immutableFacts", {})
    assert_true(immutable.get("score") == result.get("score"), "模型研判不得改写评分", immutable)
    assert_true(immutable.get("level") == result.get("level"), "模型研判不得改写等级", immutable)
```

with:

```python
    judgement = result.get("modelJudgement") or {}
    difference = result.get("modelRuleDifference") or {}
    assert_true(judgement.get("level"), "模型主导研判必须给出最终等级", judgement)
    assert_true(judgement.get("recommendedType"), "模型主导研判必须给出最终推荐方式", judgement)
    assert_true(difference.get("ruleLevel") == result.get("level"), "差异检查器必须保留规则等级基线", difference)
    assert_true(difference.get("modelLevel") == judgement.get("level"), "差异检查器必须保留模型等级", difference)
    assert_true(difference.get("reviewLabels"), "差异检查器必须输出复核标签", difference)
```

- [ ] **Step 2: Run updated legacy test**

Run:

```powershell
python .\tools\verify_model_oriented_research.py
```

Expected: PASS after Task 2 is implemented.

- [ ] **Step 3: Update the integration contract document**

In `docs/llm_integration_contract.md`, replace the “不可变事实” section with:

```markdown
## 规则基线与模型主导

LLM 是一期最终研判中枢，可以在明确说明理由、证据、置信度和复核标签的前提下覆盖规则评分对应的等级或推荐方案。后端规则评分不再是最终裁判，而是模型研判的基线、参照物和差异检查坐标。

系统必须同时保留：

- `ruleBaseline`：规则分数、规则等级、规则推荐方式、维度拆解和命中规则。
- `modelJudgement`：模型最终等级、推荐方式、置信度、判断理由、风险和补资优先级。
- `modelRuleDifference`：规则结论与模型结论的一致或覆盖关系、覆盖理由和人工复核标签。
- `modelQuality`：事实诚实性、依据覆盖、缺项影响和输出结构状态。

模型不能把缺失事实写成已确认事实。接口标高、消防分区、产权界面、管线条件、施工图审查和工程级图纸结论若未被输入资料确认，必须标注为“模型推断”或“需人工复核”。
```

Also replace any sentence saying “LLM 不得自行改分、改等级” with:

```markdown
模型可以覆盖规则等级或推荐方案，但必须保留规则基线、覆盖理由、证据引用和人工复核标签。
```

- [ ] **Step 4: Run both backend verification scripts**

Run:

```powershell
python .\tools\verify_model_led_phase_one.py
python .\tools\verify_model_oriented_research.py
```

Expected: both PASS.

- [ ] **Step 5: Commit contract update**

Run:

```powershell
git add docs/llm_integration_contract.md tools/verify_model_oriented_research.py
git commit -m "docs: update llm contract for model-led judgement"
```

Expected: commit succeeds.

## Task 4: Frontend Model-Led Dashboard and Difference Checker

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/assets/app.js`
- Modify: `frontend/assets/styles.css`
- Test: `tools/verify_model_led_ui.cjs`

- [ ] **Step 1: Write failing UI verification**

Create `tools/verify_model_led_ui.cjs` with this content:

```javascript
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const url = process.env.INTERCONNECT_URL || "http://127.0.0.1:8765/";
const resultPath = path.join(root, "model_led_ui_verify.json");
const screenshotPath = path.join(root, "model_led_ui_verify.png");

function browserExecutable() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((item) => fs.existsSync(item));
}

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1040 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message || String(error)));

  await page.goto(url, { waitUntil: "load", timeout: 30000 });
  await page.waitForFunction(() => {
    return document.querySelector("#modelJudgementTitle")
      && document.querySelector("#modelJudgementTitle").textContent.includes("模型");
  }, null, { timeout: 15000 });

  await page.waitForFunction(() => {
    const text = document.body.innerText;
    return text.includes("模型主导研判")
      && text.includes("规则基线")
      && text.includes("复核标签")
      && document.querySelectorAll("#modelRiskList .model-risk-item").length >= 3
      && document.querySelectorAll("#modelFundingList .model-funding-item").length >= 3;
  }, null, { timeout: 10000 });

  await page.click('[data-view-link="reporting"]');
  await page.waitForFunction(() => {
    return document.querySelector(".view.active")?.id === "reporting"
      && document.querySelectorAll("[data-report-mode]").length === 3
      && document.querySelector("#diagramBriefSvg svg");
  }, null, { timeout: 10000 });

  await page.click('[data-report-mode="expert_appendix"]');
  await page.waitForFunction(() => {
    return document.querySelector("[data-report-mode='expert_appendix']").classList.contains("active")
      && document.querySelector("#reportModeSummary").textContent.includes("专家");
  }, null, { timeout: 5000 });

  const summary = await page.evaluate(() => ({
    modelTitle: document.querySelector("#modelJudgementTitle")?.textContent,
    difference: document.querySelector("#modelDifferencePanel")?.textContent,
    risks: document.querySelectorAll("#modelRiskList .model-risk-item").length,
    funding: document.querySelectorAll("#modelFundingList .model-funding-item").length,
    modes: Array.from(document.querySelectorAll("[data-report-mode]")).map((node) => node.textContent.trim()),
    diagramText: document.querySelector("#diagramBriefSvg")?.textContent,
    activeMode: document.querySelector("[data-report-mode].active")?.dataset.reportMode,
  }));

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await context.close();
  await browser.close();

  const result = {
    ok: summary.modelTitle.includes("模型")
      && summary.difference.includes("规则基线")
      && summary.risks >= 3
      && summary.funding >= 3
      && summary.modes.length === 3
      && summary.diagramText.includes("推荐")
      && summary.activeMode === "expert_appendix"
      && errors.length === 0,
    summary,
    errors,
    screenshotPath,
  };
  await fsp.writeFile(resultPath, JSON.stringify(result, null, 2), "utf-8");
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 2: Run UI test to verify it fails**

Start the app in one terminal:

```powershell
.\run.ps1
```

Then run:

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_model_led_ui.cjs
```

Expected: FAIL because the model-led dashboard containers and report mode controls do not exist.

- [ ] **Step 3: Add dashboard containers**

In `frontend/index.html`, inside the dashboard hero after `dashboardPolicy`, add:

```html
<section class="model-judgement-card">
  <div>
    <span class="eyebrow">模型主导研判</span>
    <h3 id="modelJudgementTitle">模型研判待运行</h3>
    <p id="modelJudgementReason">运行评估后展示模型最终结论、覆盖理由和置信度。</p>
  </div>
  <div id="modelConfidence" class="confidence-meter">--</div>
</section>
<section id="modelDifferencePanel" class="model-difference-panel">规则基线与模型差异将在运行后展示。</section>
<div class="model-work-grid">
  <section>
    <h3>关键风险</h3>
    <div id="modelRiskList" class="model-list"></div>
  </section>
  <section>
    <h3>补资优先级</h3>
    <div id="modelFundingList" class="model-list"></div>
  </section>
</div>
```

- [ ] **Step 4: Add report mode and diagram containers**

In `frontend/index.html`, inside the reporting panel header before `reportPreview`, add:

```html
<div id="reportModeTabs" class="report-mode-tabs"></div>
<p id="reportModeSummary" class="report-mode-summary">运行评估后可切换客户正式版、专家附录版和领导汇报版。</p>
<section class="diagram-brief-panel">
  <div>
    <span class="eyebrow">示意图 brief</span>
    <h3 id="diagramBriefTitle">推荐联通路径示意</h3>
  </div>
  <div id="diagramBriefSvg" class="diagram-brief-svg"></div>
</section>
```

- [ ] **Step 5: Add frontend render helpers**

In `frontend/assets/app.js`, add these functions before `renderDashboardHero`:

```javascript
function modelJudgement(result = state.currentResult) {
  return result?.modelJudgement || {};
}

function modelDifference(result = state.currentResult) {
  return result?.modelRuleDifference || {};
}

function modelQuality(result = state.currentResult) {
  return result?.modelQuality || {};
}

function renderModelList(node, items, className) {
  if (!node) return;
  if (!items?.length) {
    node.innerHTML = `<div class="empty-state">暂无模型条目。</div>`;
    return;
  }
  node.innerHTML = items.map((item) => `
    <article class="${className}">
      <strong>${escapeHtml(item.title || item.name || item.id)}</strong>
      <p>${escapeHtml(item.detail || item.reason || item.reviewLabel || "")}</p>
      <span>${escapeHtml(item.severity || item.priority || item.reviewLabel || "复核")}</span>
    </article>
  `).join("");
}

function renderModelJudgement(result = state.currentResult) {
  const judgement = modelJudgement(result);
  const difference = modelDifference(result);
  const quality = modelQuality(result);
  const title = $("#modelJudgementTitle");
  const reason = $("#modelJudgementReason");
  const confidence = $("#modelConfidence");
  const differencePanel = $("#modelDifferencePanel");
  if (!title || !reason || !confidence || !differencePanel) return;
  if (!result || !judgement.level) {
    title.textContent = "模型研判待运行";
    reason.textContent = "运行评估后展示模型最终结论、覆盖理由和置信度。";
    confidence.textContent = "--";
    differencePanel.textContent = "规则基线与模型差异将在运行后展示。";
    renderModelList($("#modelRiskList"), [], "model-risk-item");
    renderModelList($("#modelFundingList"), [], "model-funding-item");
    return;
  }
  title.textContent = `模型建议：${judgement.level}，${judgement.recommendedType}`;
  reason.textContent = judgement.reason || "模型已基于项目资料生成综合判断。";
  confidence.textContent = `${Math.round(Number(judgement.confidence || 0) * 100)}%`;
  const labels = [...(difference.reviewLabels || []), ...(quality.labels || [])];
  differencePanel.innerHTML = `
    <strong>规则基线：${escapeHtml(difference.ruleLevel || result.level)} / ${escapeHtml(difference.ruleRecommendedType || result.recommendation?.primary?.name || "")}</strong>
    <span>模型结论：${escapeHtml(difference.modelLevel || judgement.level)} / ${escapeHtml(difference.modelRecommendedType || judgement.recommendedType)}</span>
    <p>${escapeHtml(difference.reason || judgement.overrideReason || "模型结论与规则基线一致。")}</p>
    <div>${labels.map((label) => `<b>${escapeHtml(label)}</b>`).join("")}</div>
  `;
  renderModelList($("#modelRiskList"), judgement.riskItems || [], "model-risk-item");
  renderModelList($("#modelFundingList"), judgement.fundingRequests || [], "model-funding-item");
}

function renderDiagramBrief(result = state.currentResult) {
  const brief = result?.diagramBrief || {};
  const title = $("#diagramBriefTitle");
  const node = $("#diagramBriefSvg");
  if (!title || !node) return;
  title.textContent = brief.title || "推荐联通路径示意";
  const nodes = brief.nodes || [];
  const edges = brief.edges || [];
  if (!nodes.length || !edges.length) {
    node.innerHTML = `<div class="empty-state">运行评估后生成示意图 brief。</div>`;
    return;
  }
  const byId = Object.fromEntries(nodes.map((item) => [item.id, item]));
  node.innerHTML = `
    <svg viewBox="0 0 560 280" role="img" aria-label="${escapeHtml(brief.title || "推荐联通路径示意")}">
      <rect x="18" y="24" width="524" height="216" rx="8" class="diagram-bg"></rect>
      ${edges.map((edge) => {
        const from = byId[edge.from] || nodes[0];
        const to = byId[edge.to] || nodes[nodes.length - 1];
        return `<g>
          <path d="M ${from.x} ${from.y} C ${from.x + 90} ${from.y - 70}, ${to.x - 90} ${to.y + 70}, ${to.x} ${to.y}" class="diagram-path"></path>
          <text x="${(from.x + to.x) / 2 - 48}" y="${(from.y + to.y) / 2 - 38}" class="diagram-label">${escapeHtml(edge.label || "推荐路径")}</text>
        </g>`;
      }).join("")}
      ${nodes.map((item) => `
        <g>
          <circle cx="${item.x}" cy="${item.y}" r="34" class="diagram-node ${escapeHtml(item.type || "")}"></circle>
          <text x="${item.x}" y="${item.y + 4}" text-anchor="middle" class="diagram-node-label">${escapeHtml(item.label)}</text>
        </g>
      `).join("")}
      ${(brief.annotations || []).map((item, index) => `
        <text x="52" y="${226 + index * 18}" class="diagram-note">${escapeHtml(item.text)}</text>
      `).join("")}
    </svg>
  `;
}
```

- [ ] **Step 6: Add report mode rendering**

Add near `renderReport`:

```javascript
function renderReportModes(result = state.currentResult) {
  const tabs = $("#reportModeTabs");
  const summary = $("#reportModeSummary");
  if (!tabs || !summary) return;
  const modes = result?.reportModes || [];
  if (!modes.length) {
    tabs.innerHTML = "";
    summary.textContent = "运行评估后可切换客户正式版、专家附录版和领导汇报版。";
    return;
  }
  const active = state.reportMode || modes[0].id;
  tabs.innerHTML = modes.map((mode) => `
    <button type="button" data-report-mode="${escapeHtml(mode.id)}" class="${mode.id === active ? "active" : ""}">
      ${escapeHtml(mode.name)}
    </button>
  `).join("");
  const selected = modes.find((mode) => mode.id === active) || modes[0];
  summary.textContent = `${selected.name}：${selected.tone}。重点：${selected.focus}。`;
}
```

In `state`, add:

```javascript
  reportMode: "client_formal",
```

In `renderResult`, after `renderTrace(result);`, add:

```javascript
  renderModelJudgement(result);
  renderReportModes(result);
  renderDiagramBrief(result);
```

In `renderDashboardHero`, call `renderModelJudgement(result);` before returning.

In `bindEvents`, add:

```javascript
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-report-mode]");
    if (!button) return;
    state.reportMode = button.dataset.reportMode;
    renderReportModes(state.currentResult);
  });
```

- [ ] **Step 7: Add CSS**

Append to `frontend/assets/styles.css`:

```css
.model-judgement-card,
.diagram-brief-panel {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.confidence-meter {
  min-width: 76px;
  height: 76px;
  border-radius: 50%;
  border: 8px solid #2f6fed;
  display: grid;
  place-items: center;
  font-weight: 700;
  color: #173b7a;
}

.model-difference-panel {
  border-left: 4px solid #2f6fed;
  background: #f5f8ff;
  padding: 12px 14px;
  border-radius: 6px;
}

.model-difference-panel b {
  display: inline-block;
  margin: 8px 6px 0 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e7eefc;
  color: #173b7a;
  font-size: 12px;
}

.model-work-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.model-risk-item,
.model-funding-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  margin-bottom: 8px;
}

.model-risk-item span,
.model-funding-item span {
  color: #8a4b00;
  font-size: 12px;
  font-weight: 700;
}

.report-mode-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.report-mode-tabs button {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
  padding: 8px 12px;
  cursor: pointer;
}

.report-mode-tabs button.active {
  border-color: #2f6fed;
  color: #173b7a;
  background: #eef4ff;
  font-weight: 700;
}

.diagram-brief-svg {
  width: 100%;
  min-height: 240px;
}

.diagram-brief-svg svg {
  width: 100%;
  height: auto;
}

.diagram-bg {
  fill: #f8fafc;
  stroke: #d8dee9;
}

.diagram-path {
  fill: none;
  stroke: #2f6fed;
  stroke-width: 10;
  stroke-linecap: round;
}

.diagram-node {
  fill: #ffffff;
  stroke: #111827;
  stroke-width: 2;
}

.diagram-node.station {
  fill: #efe8ff;
}

.diagram-node.parcel {
  fill: #fff7ed;
}

.diagram-node-label,
.diagram-label,
.diagram-note {
  font-size: 13px;
  fill: #111827;
}
```

- [ ] **Step 8: Run UI test to green**

Run:

```powershell
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_model_led_ui.cjs
```

Expected: PASS with `ok: true`.

- [ ] **Step 9: Commit frontend**

Run:

```powershell
git add frontend/index.html frontend/assets/app.js frontend/assets/styles.css tools/verify_model_led_ui.cjs
git commit -m "feat: surface model-led phase one UI"
```

Expected: commit succeeds.

## Task 5: Export and Documentation Alignment

**Files:**
- Modify: `backend/server.py`
- Modify: `README.md`
- Modify: `docs/api_reference.md`
- Test: existing full verification and export scripts

- [ ] **Step 1: Add failing export verification**

In `tools/verify_model_led_phase_one.py`, after `diagram = result.get("diagramBrief") or {}`, add:

```python
    snapshot_keys = {"modelJudgement", "modelRuleDifference", "modelQuality", "diagramBrief", "reportModes"}
    assert_true(snapshot_keys.issubset(result.keys()), "导出快照所需模型主导字段缺失", sorted(result.keys()))
```

- [ ] **Step 2: Ensure export JSON includes model-led fields**

In `backend/server.py`, inspect `export_report_file`. If the JSON snapshot writes the complete `result`, no code change is needed. If it builds a reduced dict, include:

```python
"modelJudgement": result.get("modelJudgement"),
"modelRuleDifference": result.get("modelRuleDifference"),
"modelQuality": result.get("modelQuality"),
"diagramBrief": result.get("diagramBrief"),
"reportModes": result.get("reportModes"),
```

- [ ] **Step 3: Update API reference**

In `docs/api_reference.md`, under `POST /api/evaluate`, add:

```markdown
### 模型主导字段

- `modelJudgement`：模型最终等级、推荐方式、置信度、覆盖理由、风险项和补资优先级。
- `modelRuleDifference`：规则基线与模型结论的差异状态、规则等级、模型等级、规则推荐、模型推荐和复核标签。
- `modelQuality`：事实诚实性、依据覆盖、缺项影响和质量标签。
- `diagramBrief`：一期示意图的结构化 brief，可用于 SVG 预览和报告嵌入。
- `reportModes`：客户正式版、专家附录版、领导汇报版三类报告模式。
```

- [ ] **Step 4: Update README verification commands**

In `README.md`, add the new verification commands:

```powershell
python .\tools\verify_model_led_phase_one.py
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_model_led_ui.cjs
```

- [ ] **Step 5: Run full verification**

Run:

```powershell
python -m py_compile .\backend\server.py .\backend\research_agent.py .\tools\verify_model_led_phase_one.py .\tools\verify_model_oriented_research.py
python .\tools\verify_model_led_phase_one.py
python .\tools\verify_model_oriented_research.py
$env:NODE_PATH='C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\verify_system.cjs
& 'C:\Users\R\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' .\tools\verify_model_led_ui.cjs
```

Expected: all commands PASS.

- [ ] **Step 6: Commit final alignment**

Run:

```powershell
git add backend/server.py README.md docs/api_reference.md tools/verify_model_led_phase_one.py
git commit -m "docs: document model-led phase one outputs"
```

Expected: commit succeeds.

## Self-Review

- Spec coverage: Tasks cover model-led judgement, rule/model difference, quality labels, customer dashboard, implementation review view, three report modes, SVG diagram brief, fallback honesty, docs, and verification.
- Placeholder scan: no TODO/TBD/fill-in-later steps remain; code snippets and expected commands are provided.
- Type consistency: `modelJudgement`, `modelRuleDifference`, `modelQuality`, `diagramBrief`, and `reportModes` are introduced in backend and used consistently by frontend and tests.
