## 1. Source Analysis And Normalization

- [x] 1.1 Document the 0528 workbook sheet layout, horizons, direction labels, and unsupported/blank rows.
- [x] 1.2 Add an ingestion path that reads or converts the legacy `.xls` source and emits deterministic normalized JSON.
- [x] 1.3 Add validation checks for expected line sheets, station counts, numeric boarding/alighting values, and source metadata.

## 2. Data Integration

- [x] 2.1 Add `data/ridership_forecast.json` and load it in backend bootstrap/station context.
- [x] 2.2 Join forecast records to station search/context by alias and line while preserving ambiguous matches.
- [x] 2.3 Update frontend station context display to show observed and forecast客流 separately.

## 3. Report And Verification

- [x] 3.1 Update report evidence builders to include current-vs-forecast客流 wording when forecast data exists.
- [x] 3.2 Add backend and frontend verification for forecast context lookup, ambiguous station matches, and report text.
- [x] 3.3 Update docs/source manifest to include the 0528 workbook and its parsing/conversion requirements.
