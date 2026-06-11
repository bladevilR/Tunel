from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
DEFAULT_WORKBOOK = WORKSPACE / "0528既有线路客流预测数据.xls"
DEFAULT_OUTPUT = ROOT / "data" / "ridership_forecast.json"
VERSION = "ridership-forecast.v1"
SOURCE_FILE_NAME = "0528既有线路客流预测数据.xls"


@dataclass(frozen=True)
class SheetSpec:
    line: str
    sheet: str
    station_count: int
    horizons: tuple[int, int]
    directions: tuple[str, str]


SHEET_SPECS = [
    SheetSpec("2", "2号线", 33, (2024, 2039), ("由北向南", "由南向北")),
    SheetSpec("3", "3号线", 37, (2029, 2044), ("由西向东", "由东向西")),
    SheetSpec("4", "4号线", 31, (2026, 2041), ("由北向南", "由南向北")),
    SheetSpec("5", "5号线", 34, (2029, 2044), ("由西向东", "由东向西")),
    SheetSpec("6", "6号线", 30, (2033, 2048), ("由西向东", "由东向西")),
    SheetSpec("7", "7号线", 32, (2034, 2049), ("由北向南", "由南向北")),
    SheetSpec("8", "8号线", 28, (2033, 2048), ("由北向南", "由南向北")),
    SheetSpec("11", "11号线", 28, (2032, 2047), ("由西向东", "由东向西")),
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def workbook_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ace_extended_properties(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".xls":
        return "Excel 8.0;HDR=NO;IMEX=1"
    if suffix in {".xlsx", ".xlsm"}:
        return "Excel 12.0 Xml;HDR=NO;IMEX=1"
    raise ValueError(f"unsupported workbook extension: {path.suffix}")


def powershell_executable() -> str:
    for candidate in ("powershell", "pwsh"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise RuntimeError("PowerShell is required for ACE/OLEDB workbook extraction")


def read_workbook_via_ace(path: Path) -> dict:
    script = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Data
$path = [Environment]::GetEnvironmentVariable('RIDERSHIP_FORECAST_WORKBOOK')
$extended = [Environment]::GetEnvironmentVariable('RIDERSHIP_FORECAST_EXTENDED_PROPERTIES')
$sheetNames = @('2号线$', '3号线$', '4号线$', '5号线$', '6号线$', '7号线$', '8号线$', '11号线$')
$connString = "Provider=Microsoft.ACE.OLEDB.12.0;Data Source=$path;Extended Properties='$extended'"
$conn = [System.Data.OleDb.OleDbConnection]::new($connString)
$result = [ordered]@{ availableSheets = @(); sheets = @() }
try {
    $conn.Open()
    $schema = $conn.GetOleDbSchemaTable([System.Data.OleDb.OleDbSchemaGuid]::Tables, $null)
    foreach ($row in $schema.Rows) {
        $name = [string]$row.TABLE_NAME
        $trimmed = $name.Trim("'")
        if ($trimmed.EndsWith('$')) {
            $result.availableSheets += $trimmed.TrimEnd('$')
        }
    }
    foreach ($sheetName in $sheetNames) {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT * FROM [$sheetName]"
        $adapter = [System.Data.OleDb.OleDbDataAdapter]::new($cmd)
        $table = [System.Data.DataTable]::new()
        [void]$adapter.Fill($table)
        $rows = @()
        foreach ($dataRow in $table.Rows) {
            $cells = @()
            foreach ($column in $table.Columns) {
                $value = $dataRow[$column.ColumnName]
                if ($null -eq $value -or $value -is [DBNull]) {
                    $cells += $null
                } else {
                    $cells += $value
                }
            }
            $rows += ,$cells
        }
        $result.sheets += [ordered]@{
            name = $sheetName.TrimEnd('$')
            rowCount = $table.Rows.Count
            columnCount = $table.Columns.Count
            rows = $rows
        }
    }
} finally {
    $conn.Close()
}
$result | ConvertTo-Json -Depth 8 -Compress
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    env = {
        **os.environ,
        "RIDERSHIP_FORECAST_WORKBOOK": str(path),
        "RIDERSHIP_FORECAST_EXTENDED_PROPERTIES": ace_extended_properties(path),
    }
    completed = subprocess.run(
        [
            powershell_executable(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "ACE/OLEDB workbook extraction failed. "
            "Install Microsoft Access Database Engine or convert the workbook to .xlsx and rerun.\n"
            f"{completed.stderr.strip()}"
        )
    return json.loads(completed.stdout.lstrip("\ufeff"))


def parse_header(text: str, spec: SheetSpec, column: int) -> dict:
    label_match = re.search(r"(近期|远期)", text)
    year_match = re.search(r"(\d{4})\s*年", text)
    line_match = re.search(r"(\d+)\s*号线", text)
    if not label_match or not year_match or not line_match:
        raise ValueError(f"{spec.sheet} column {column + 1} has invalid horizon header: {text!r}")
    if line_match.group(1) != spec.line:
        raise ValueError(f"{spec.sheet} header line mismatch: {text!r}")
    return {
        "label": label_match.group(1),
        "year": int(year_match.group(1)),
        "startColumn": column,
        "rawHeader": text,
    }


def cell(row: list[Any], index: int) -> Any:
    if index >= len(row):
        return None
    return row[index]


def number(value: Any, context: str) -> int:
    text = clean(value)
    if text == "":
        raise ValueError(f"missing numeric value at {context}")
    try:
        parsed = float(text.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"non-numeric value at {context}: {text!r}") from exc
    if not math.isfinite(parsed) or parsed < 0 or not parsed.is_integer():
        raise ValueError(f"invalid count at {context}: {text!r}")
    return int(parsed)


def discover_tables(rows: list[list[Any]], spec: SheetSpec) -> list[dict]:
    if len(rows) < 4:
        raise ValueError(f"{spec.sheet} is too short to contain forecast data")
    headers: list[dict] = []
    for column, value in enumerate(rows[0]):
        text = clean(value)
        if "全日客流量预测表" in text:
            headers.append(parse_header(text, spec, column))
    if len(headers) != 2:
        raise ValueError(f"{spec.sheet} expected 2 forecast tables, found {len(headers)}")
    headers.sort(key=lambda item: item["startColumn"])
    labels = [item["label"] for item in headers]
    years = [item["year"] for item in headers]
    if labels != ["近期", "远期"]:
        raise ValueError(f"{spec.sheet} horizon labels mismatch: {labels}")
    if years != list(spec.horizons):
        raise ValueError(f"{spec.sheet} horizon years mismatch: {years}")

    for table in headers:
        start = table["startColumn"]
        station_label = clean(cell(rows[1], start + 2))
        if station_label != "车站名称":
            raise ValueError(f"{spec.sheet} missing station-name header at column {start + 3}")
        directions = [clean(cell(rows[1], start)), clean(cell(rows[1], start + 3))]
        if directions != list(spec.directions):
            raise ValueError(f"{spec.sheet} direction labels mismatch: {directions}")
        metrics = [
            clean(cell(rows[2], start)),
            clean(cell(rows[2], start + 1)),
            clean(cell(rows[2], start + 3)),
            clean(cell(rows[2], start + 4)),
        ]
        if metrics != ["上车", "下车", "上车", "下车"]:
            raise ValueError(f"{spec.sheet} metric labels mismatch: {metrics}")
        table["directions"] = directions
    return headers


def parse_sheet(sheet: dict, spec: SheetSpec, source_name: str) -> tuple[list[dict], list[str], int]:
    rows = sheet.get("rows") or []
    tables = discover_tables(rows, spec)
    records: list[dict] = []
    station_names: list[str] = []
    blank_rows = 0

    for row_number, row in enumerate(rows[3:], start=4):
        station_values = [clean(cell(row, table["startColumn"] + 2)) for table in tables]
        relevant_values: list[str] = []
        for table in tables:
            start = table["startColumn"]
            relevant_values.extend(clean(cell(row, start + offset)) for offset in (0, 1, 2, 3, 4))

        if not any(station_values):
            if any(relevant_values):
                raise ValueError(f"{spec.sheet} row {row_number} has values but no station name")
            blank_rows += 1
            continue
        if station_values[0] != station_values[1]:
            raise ValueError(f"{spec.sheet} row {row_number} station mismatch: {station_values}")

        station_name = station_values[0]
        station_names.append(station_name)
        for table in tables:
            start = table["startColumn"]
            for direction_index, direction_offset in enumerate((0, 3)):
                direction = spec.directions[direction_index]
                records.append({
                    "line": spec.line,
                    "lineLabel": spec.sheet,
                    "stationName": station_name,
                    "horizonLabel": table["label"],
                    "horizonYear": table["year"],
                    "directionLabel": direction,
                    "boarding": number(cell(row, start + direction_offset), f"{spec.sheet} R{row_number} {table['label']} {direction} 上车"),
                    "alighting": number(cell(row, start + direction_offset + 1), f"{spec.sheet} R{row_number} {table['label']} {direction} 下车"),
                    "sourceSheet": spec.sheet,
                    "source": source_name,
                })

    if len(station_names) != spec.station_count:
        raise ValueError(f"{spec.sheet} expected {spec.station_count} station rows, found {len(station_names)}")
    duplicates = sorted({name for name in station_names if station_names.count(name) > 1})
    if duplicates:
        raise ValueError(f"{spec.sheet} duplicate station names: {duplicates}")
    expected_records = spec.station_count * len(spec.horizons) * len(spec.directions)
    if len(records) != expected_records:
        raise ValueError(f"{spec.sheet} expected {expected_records} records, found {len(records)}")
    return records, station_names, blank_rows


def build_rollups(records: list[dict], station_order_by_line: dict[str, list[str]], source_name: str) -> list[dict]:
    by_station: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        by_station.setdefault((record["line"], record["stationName"]), []).append(record)

    rollups: list[dict] = []
    specs_by_line = {spec.line: spec for spec in SHEET_SPECS}
    for spec in SHEET_SPECS:
        for station_name in station_order_by_line[spec.line]:
            station_records = by_station[(spec.line, station_name)]
            by_horizon = []
            for horizon in spec.horizons:
                horizon_records = [item for item in station_records if item["horizonYear"] == horizon]
                directions = []
                for direction in spec.directions:
                    record = next(item for item in horizon_records if item["directionLabel"] == direction)
                    directions.append({
                        "directionLabel": direction,
                        "boarding": record["boarding"],
                        "alighting": record["alighting"],
                    })
                by_horizon.append({
                    "horizonYear": horizon,
                    "horizonLabel": next(item["horizonLabel"] for item in horizon_records),
                    "boardingTotal": sum(item["boarding"] for item in horizon_records),
                    "alightingTotal": sum(item["alighting"] for item in horizon_records),
                    "directions": directions,
                })
            rollups.append({
                "line": spec.line,
                "lineLabel": specs_by_line[spec.line].sheet,
                "stationName": station_name,
                "sourceSheet": spec.sheet,
                "source": source_name,
                "byHorizon": by_horizon,
            })
    return rollups


def normalize(raw_workbook: dict, workbook: Path) -> dict:
    expected_sheets = [spec.sheet for spec in SHEET_SPECS]
    available_sheets = raw_workbook.get("availableSheets") or []
    if set(available_sheets) != set(expected_sheets):
        raise ValueError(f"workbook sheets mismatch: expected {expected_sheets}, found {available_sheets}")

    sheets_by_name = {sheet["name"]: sheet for sheet in raw_workbook.get("sheets", [])}
    records: list[dict] = []
    station_order_by_line: dict[str, list[str]] = {}
    blank_rows_by_line: dict[str, int] = {}
    raw_rows_by_line: dict[str, int] = {}
    raw_columns_by_line: dict[str, int] = {}
    for spec in SHEET_SPECS:
        if spec.sheet not in sheets_by_name:
            raise ValueError(f"missing sheet data for {spec.sheet}")
        sheet_records, station_names, blank_rows = parse_sheet(sheets_by_name[spec.sheet], spec, workbook.name)
        records.extend(sheet_records)
        station_order_by_line[spec.line] = station_names
        blank_rows_by_line[spec.line] = blank_rows
        raw_rows_by_line[spec.line] = int(sheets_by_name[spec.sheet].get("rowCount") or 0)
        raw_columns_by_line[spec.line] = int(sheets_by_name[spec.sheet].get("columnCount") or 0)

    rollups = build_rollups(records, station_order_by_line, workbook.name)
    return {
        "version": VERSION,
        "metric": "全日客流量预测",
        "unit": "人次",
        "source": {
            "fileName": workbook.name,
            "canonicalFileName": SOURCE_FILE_NAME,
            "format": "legacy-xls" if workbook.suffix.lower() == ".xls" else workbook.suffix.lower().lstrip("."),
            "reader": "PowerShell ACE/OLEDB",
            "sizeBytes": workbook.stat().st_size,
            "sha256": workbook_sha256(workbook),
        },
        "counts": {
            "lineCount": len(SHEET_SPECS),
            "recordCount": len(records),
            "stationRollupCount": len(rollups),
        },
        "validation": {
            "expectedSheets": expected_sheets,
            "horizonsByLine": {spec.line: list(spec.horizons) for spec in SHEET_SPECS},
            "directionsByLine": {spec.line: list(spec.directions) for spec in SHEET_SPECS},
            "stationCountsByLine": {spec.line: spec.station_count for spec in SHEET_SPECS},
            "blankRowsByLine": blank_rows_by_line,
            "rawRowsByLine": raw_rows_by_line,
            "rawColumnsByLine": raw_columns_by_line,
        },
        "records": records,
        "stationRollups": rollups,
    }


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize the 0528 legacy xls ridership forecast workbook.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK, help="Source .xls/.xlsx workbook path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Normalized JSON output path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    workbook = args.workbook.resolve()
    if not workbook.exists():
        raise FileNotFoundError(f"source workbook not found: {workbook}")
    raw_workbook = read_workbook_via_ace(workbook)
    payload = normalize(raw_workbook, workbook)
    write_payload(args.output, payload)
    print(json.dumps({
        "ok": True,
        "source": str(workbook),
        "output": str(args.output.resolve()),
        "records": payload["counts"]["recordCount"],
        "stationRollups": payload["counts"]["stationRollupCount"],
        "stationCountsByLine": payload["validation"]["stationCountsByLine"],
        "blankRowsByLine": payload["validation"]["blankRowsByLine"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
