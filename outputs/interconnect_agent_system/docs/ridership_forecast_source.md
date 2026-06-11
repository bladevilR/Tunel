# Ridership Forecast Source Normalization

## Source

- Workbook: `0528既有线路客流预测数据.xls`
- Format: legacy OLE2 `.xls`
- Metric: `全日客流量预测`
- Unit: `人次`
- Runtime artifact: `outputs/interconnect_agent_system/data/ridership_forecast.json`
- Ingestion script: `outputs/interconnect_agent_system/tools/ingest_ridership_forecast.py`

## Workbook Layout

Each supported sheet stores two forecast tables side by side. Row 1 names the horizon and year, row 2 contains two directional labels around `车站名称`, and row 3 contains `上车` / `下车` metric labels. Data rows start at row 4.

| Sheet | Horizons | Directions | Station rows | Blank or unsupported rows |
|---|---|---|---:|---|
| `2号线` | 近期 2024, 远期 2039 | 由北向南, 由南向北 | 33 | none |
| `3号线` | 近期 2029, 远期 2044 | 由西向东, 由东向西 | 37 | none |
| `4号线` | 近期 2026, 远期 2041 | 由北向南, 由南向北 | 31 | none |
| `5号线` | 近期 2029, 远期 2044 | 由西向东, 由东向西 | 34 | none |
| `6号线` | 近期 2033, 远期 2048 | 由西向东, 由东向西 | 30 | none |
| `7号线` | 近期 2034, 远期 2049 | 由北向南, 由南向北 | 32 | ACE/OLEDB reports a large used range; 245 trailing blank data rows are skipped |
| `8号线` | 近期 2033, 远期 2048 | 由北向南, 由南向北 | 28 | none |
| `11号线` | 近期 2032, 远期 2047 | 由西向东, 由东向西 | 28 | none |

No unsupported non-station rows are accepted. A row with metric values but no station name, mismatched near/far station names, missing numeric counts, negative counts, or non-integer counts fails ingestion.

## Normalized Output

The JSON output preserves each station, line, horizon year, direction label, boarding count, alighting count, source sheet, and source workbook name. It also includes station-line rollups under `stationRollups`; each rollup aggregates boarding and alighting totals by horizon while retaining the directional detail.

The artifact is deterministic: it does not include generation timestamps or absolute paths. Source traceability is captured through workbook file name, file size, and SHA-256.

## Ingestion Path

Primary path on Windows:

```powershell
python .\outputs\interconnect_agent_system\tools\ingest_ridership_forecast.py
python .\outputs\interconnect_agent_system\tools\verify_ridership_forecast_ingestion.py
```

The script uses PowerShell ACE/OLEDB to read the legacy `.xls` workbook and Python standard-library code to validate and write JSON. It does not require pandas or `xlrd`.

If ACE/OLEDB is unavailable, install the Microsoft Access Database Engine provider or use Excel/LibreOffice to convert the workbook to `.xlsx`, then rerun:

```powershell
python .\outputs\interconnect_agent_system\tools\ingest_ridership_forecast.py --workbook .\0528既有线路客流预测数据.xlsx
```

The committed `ridership_forecast.json` should be regenerated from the original `.xls` source when the ACE/OLEDB path is available.
