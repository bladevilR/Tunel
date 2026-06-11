## Why

The original feedback said current ridership should use the monthly inbound workbook first, with forecast ridership to be added later. The new `0528既有线路客流预测数据.xls` is now present and contains line-by-line 2032 and 2047 directional boarding/alighting forecasts that are not yet represented in station context, reports, or knowledge data.

## What Changes

- Add a normalized ridership forecast dataset derived from the 0528 workbook.
- Preserve the workbook's line, station, horizon year, direction, boarding, and alighting values.
- Expose forecast records through station context APIs and frontend station cards alongside existing 2025 daily inbound data.
- Make report text distinguish current observed ridership from forecast ridership, including source and horizon year.
- Add parsing and validation coverage for legacy `.xls` source handling or a documented conversion fallback.

## Capabilities

### New Capabilities

- `ridership-forecast-data`: Forecast ridership ingestion, normalization, station lookup, and report usage.

### Modified Capabilities

## Impact

- New data artifact under `outputs/interconnect_agent_system/data/`.
- Knowledge builder and ingestion tooling.
- Backend station context and bootstrap payloads.
- Frontend station search/autofill displays.
- Report evidence and exported content.
- Deployment notes for legacy `.xls` parsing or conversion prerequisites.
