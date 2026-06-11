from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import server  # noqa: E402
from backend.research_agent import report_ridership_notice  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    payload = server.RIDERSHIP_FORECAST
    records = payload.get("records") or []
    require(records, "ridership forecast records must load")
    require(payload.get("source", {}).get("fileName") == "0528既有线路客流预测数据.xls", "source workbook must be preserved")

    ambiguous_name = "高铁苏州北站"
    all_line_context = server.station_context_payload(ambiguous_name)
    all_forecast = all_line_context.get("ridershipForecast") or {}
    require({"2", "7"}.issubset(set(all_forecast.get("lines") or [])), "ambiguous station should expose all matching forecast lines")
    require(all_forecast.get("count", 0) >= 8, "ambiguous station should not collapse forecast records")

    line_context = server.station_context_payload(ambiguous_name, {"line": "2"})
    line_forecast = line_context.get("ridershipForecast") or {}
    require(line_forecast.get("lines") == ["2"], "line override should filter forecast records")
    require({item.get("horizonYear") for item in line_forecast.get("horizons") or []} == {2024, 2039}, "line 2 horizons should be preserved")
    require(line_context.get("ridership") is not line_context.get("ridershipForecast"), "forecast data must stay separate from observed ridership")

    notice = report_ridership_notice({
        "dailyInbound": 1234,
        "dailyInboundSource": "observed ridership fixture",
        "ridershipForecast": line_forecast,
    })
    require("预测客流补充" in notice, "report should include forecast evidence wording")
    require("0528既有线路客流预测数据.xls" in notice, "report should cite forecast workbook")
    require("不作为当前实测日均进站值" in notice, "report must not present forecast as current observed ridership")

    print(json.dumps({
        "ok": True,
        "station": ambiguous_name,
        "allLines": all_forecast.get("lines"),
        "lineFiltered": line_forecast.get("lines"),
        "horizons": [item.get("horizonYear") for item in line_forecast.get("horizons") or []],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
