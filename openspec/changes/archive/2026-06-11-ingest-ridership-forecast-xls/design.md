## Context

The system currently uses `data/ridership.json`, sourced from `每站每月日均进站.xlsx`, for 2025 monthly observed daily inbound values. The new workbook is an OLE2 `.xls` file with sheets for lines 2, 3, 4, 5, 6, 7, 8, and 11. Each sheet stores "近期（2032年）" and "远期（2047年）" forecast tables side by side, with station names and directional boarding/alighting counts.

## Goals / Non-Goals

**Goals:**

- Produce a repeatable normalized JSON dataset from the 0528 source.
- Join forecast records by station aliases and line numbers without overwriting observed ridership.
- Let reports cite forecast values as future-horizon evidence, not as current measured客流.

**Non-Goals:**

- Recalculate forecast models or infer high-peak-hour values that are not in the workbook.
- Change scoring thresholds unless a future scoring-spec update explicitly requests forecast-based scoring.

## Decisions

- Store forecast records separately as `ridership_forecast.json` instead of merging into `ridership.json`. This keeps observed and forecast口径 clean.
- Normalize each station-direction-horizon as a record with fields: `line`, `stationName`, `horizonYear`, `directionLabel`, `boarding`, `alighting`, `sourceSheet`, and `source`.
- Add station-level rollups for context display, such as total forecast boardings/alightings by horizon and a compact directional summary.
- Treat `.xls` ingestion as a build-time concern. If the runtime environment cannot parse `.xls` directly, the ingestion task may use a documented conversion or Windows ACE/OLEDB path, but the committed normalized JSON must be deterministic and testable.

## Risks / Trade-offs

- Legacy `.xls` parsing support varies by environment. Mitigation: make the normalized JSON the runtime artifact and document the accepted ingestion path.
- Some stations appear on multiple lines or transfer sheets. Mitigation: join by station plus line where possible and expose ambiguity instead of silently choosing one.
- Forecast values may not map directly to existing daily inbound scoring thresholds. Mitigation: reports describe forecast influence qualitatively unless scoring changes are separately approved.
