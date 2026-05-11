from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def build_template() -> None:
    target = DOCS / "pilot_input_template.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "项目录入"
    headers = [
        "研究地块/项目名称", "地块编号", "所属区划", "车站名称", "线路", "TOD级别", "区位能级", "站点类型", "日均进站量", "邻近出入口", "接口条件",
        "地块位置", "地块象限", "圈层", "用地功能", "用地性质", "功能业态", "用地面积", "建筑面积", "开发强度", "地下空间", "地下空间说明",
        "规划指标", "功能需求", "特殊约束", "附件资料", "人工复核意见"
    ]
    ws.append(headers)
    ws.append([
        "金家堰邻里中心", "6-JJY-2026-001", "工业园区", "金家堰", "6", "组团级TOD", "community", "normal", "", "3号口",
        "站厅非付费区预留远期接驳接口，接口位置与地块地下空间竖向标高匹配",
        "金堰路东、东宏路北", "东北象限", "200m核心开发区", "major_public_commercial", "商业用地", "综合性社区邻里中心",
        25000, 90000, "30k_100k", "commercial_public_pr", "有地下室，地下2层，包含停车、公共服务和商业配套空间",
        "容积率≤2.5，建筑密度≤50%，建筑限高60m", "全天候接驳、无障碍通行、轨道客流与邻里中心双向引流",
        "需与金家堰站3号口邻里中心地块互联互通方案持续对接", "地块控制性详细规划图则；地块规划条件；地块概念设计方案", ""
    ])
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max(len(str(cell.value or "")) for cell in col) + 2, 38)

    notes = wb.create_sheet("字段说明")
    notes.append(["字段", "说明", "示例/枚举"])
    for row in [
        ("区位能级", "评分因子：区位属性", "city / district / community / general"),
        ("站点类型", "评分因子：高效换乘", "current_transfer / planned_transfer / normal"),
        ("用地功能", "评分因子：用地功能", "transport_hub / major_public_commercial / general_public_commercial / office_school_residential / industrial_municipal"),
        ("开发强度", "可由建筑面积自动推断，也可人工覆盖", "gt_100k / 30k_100k / 5k_30k / lt_5k"),
        ("地下空间", "评分因子：地下属性", "commercial_public_pr / parking / other / none"),
        ("日均进站量", "可留空，系统会优先匹配20260507客流表；人工填写时覆盖预设数据", "整数，人次/日"),
        ("规划指标", "参照标准输入要素.docx", "容积率、建筑密度、建筑限高等"),
        ("附件资料", "非必须，用于人工复核和后续报告补充", "控规图则 / 规划条件 / 概念方案"),
        ("特殊约束", "用于后续规则库增强", "古城保护、地下遗址、既有站改造、分期建设等"),
    ]:
        notes.append(row)
    for col in notes.columns:
        notes.column_dimensions[col[0].column_letter].width = 42

    wb.save(target)


if __name__ == "__main__":
    build_template()
