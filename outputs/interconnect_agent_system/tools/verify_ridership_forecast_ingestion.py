from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "ridership_forecast.json"
SCRIPT_PATH = ROOT / "tools" / "ingest_ridership_forecast.py"
DOC_PATH = ROOT / "docs" / "ridership_forecast_source.md"
SOURCE_WORKBOOK = "0528既有线路客流预测数据.xls"

EXPECTED_STATION_COUNTS = {
    "2": 33,
    "3": 37,
    "4": 31,
    "5": 34,
    "6": 30,
    "7": 32,
    "8": 28,
    "11": 28,
}

EXPECTED_HORIZONS = {
    "2": [2024, 2039],
    "3": [2029, 2044],
    "4": [2026, 2041],
    "5": [2029, 2044],
    "6": [2033, 2048],
    "7": [2034, 2049],
    "8": [2033, 2048],
    "11": [2032, 2047],
}

EXPECTED_DIRECTIONS = {
    "2": ["由北向南", "由南向北"],
    "3": ["由西向东", "由东向西"],
    "4": ["由北向南", "由南向北"],
    "5": ["由西向东", "由东向西"],
    "6": ["由西向东", "由东向西"],
    "7": ["由北向南", "由南向北"],
    "8": ["由北向南", "由南向北"],
    "11": ["由西向东", "由东向西"],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_payload() -> dict:
    require(SCRIPT_PATH.exists(), f"missing ingestion script: {SCRIPT_PATH}")
    require(DATA_PATH.exists(), f"missing normalized forecast data: {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_record(records: list[dict], **criteria: object) -> dict:
    for record in records:
        if all(record.get(key) == value for key, value in criteria.items()):
            return record
    raise AssertionError(f"missing record matching {criteria}")


def main() -> None:
    payload = load_payload()
    records = payload.get("records") or []
    rollups = payload.get("stationRollups") or []
    source = payload.get("source") or {}
    validation = payload.get("validation") or {}

    expected_records = sum(EXPECTED_STATION_COUNTS.values()) * 4
    require(payload.get("version") == "ridership-forecast.v1", "unexpected payload version")
    require(source.get("fileName") == SOURCE_WORKBOOK, "source workbook name must be preserved")
    require(source.get("format") == "legacy-xls", "source format must describe the legacy xls")
    require(bool(source.get("sha256")), "source sha256 must be present")
    require(validation.get("expectedSheets") == [f"{line}号线" for line in EXPECTED_STATION_COUNTS], "unexpected sheet list")
    require(validation.get("horizonsByLine") == EXPECTED_HORIZONS, "unexpected horizons by line")
    require(validation.get("stationCountsByLine") == EXPECTED_STATION_COUNTS, "unexpected station counts")
    require(len(records) == expected_records, f"expected {expected_records} records, got {len(records)}")
    require(len(rollups) == sum(EXPECTED_STATION_COUNTS.values()), "unexpected station rollup count")

    per_line: dict[str, int] = {line: 0 for line in EXPECTED_STATION_COUNTS}
    seen_station_horizons: set[tuple[str, str, int]] = set()
    for record in records:
        line = record.get("line")
        require(line in EXPECTED_STATION_COUNTS, f"unexpected line: {line}")
        require(record.get("horizonYear") in EXPECTED_HORIZONS[line], f"unexpected horizon: {record}")
        require(record.get("directionLabel") in EXPECTED_DIRECTIONS[line], f"unexpected direction: {record}")
        require(record.get("source") == SOURCE_WORKBOOK, "record source must preserve workbook name")
        require(record.get("sourceSheet") == f"{line}号线", "record source sheet must preserve line sheet")
        require(isinstance(record.get("boarding"), int), f"boarding must be int: {record}")
        require(isinstance(record.get("alighting"), int), f"alighting must be int: {record}")
        require(record["boarding"] >= 0 and record["alighting"] >= 0, f"counts must be non-negative: {record}")
        per_line[line] += 1
        seen_station_horizons.add((line, record["stationName"], record["horizonYear"]))

    for line, station_count in EXPECTED_STATION_COUNTS.items():
        require(per_line[line] == station_count * 4, f"line {line} record count mismatch")

    first = find_record(
        records,
        line="2",
        stationName="高铁苏州北站",
        horizonYear=2024,
        directionLabel="由北向南",
    )
    require(first["boarding"] == 30064 and first["alighting"] == 0, "line 2 first station values changed")
    far = find_record(
        records,
        line="2",
        stationName="高铁苏州北站",
        horizonYear=2039,
        directionLabel="由南向北",
    )
    require(far["boarding"] == 0 and far["alighting"] == 44829, "line 2 far-horizon values changed")

    rollup = next(
        item for item in rollups
        if item.get("line") == "2" and item.get("stationName") == "高铁苏州北站"
    )
    by_year = {item["horizonYear"]: item for item in rollup.get("byHorizon", [])}
    require(by_year[2024]["boardingTotal"] == 30064, "near rollup boarding total mismatch")
    require(by_year[2024]["alightingTotal"] == 30089, "near rollup alighting total mismatch")
    require(by_year[2039]["boardingTotal"] == 43982, "far rollup boarding total mismatch")
    require(by_year[2039]["alightingTotal"] == 44829, "far rollup alighting total mismatch")

    require(DOC_PATH.exists(), f"missing source documentation: {DOC_PATH}")
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    require(SOURCE_WORKBOOK in doc_text, "source documentation must name the workbook")
    require("ACE/OLEDB" in doc_text, "source documentation must describe the ACE/OLEDB path")
    require("7号线" in doc_text and "trailing blank" in doc_text, "source documentation must note 7号线 blank rows")

    print(json.dumps({
        "ok": True,
        "records": len(records),
        "stationRollups": len(rollups),
        "lines": sorted(per_line, key=lambda item: int(item)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
