# Deployment And Server Migration Notes

This delivery runs as a local HTTP service and keeps mutable data on disk. Use this note when moving it from a workstation to a shared server.

## Runtime

- Python runtime: use the bundled Python in Codex or install Python 3.11+.
- Node runtime: required for schematic PNG export through `frontend/schematic/export_current_view.cjs`.
- Browser runtime: Chrome or Microsoft Edge must be installed on the server for PNG capture.
- Python packages: install `requirements-server.txt`. DOCX and evaluation snapshot JSON are mandatory report artifacts. PDF conversion is optional and only runs when `INTERCONNECT_EXPORT_PDF=1` or `EXPORT_PDF=1`.

## Host And Port

- `INTERCONNECT_HOST` or `HOST`: bind address, default `0.0.0.0`.
- `INTERCONNECT_PORT` or `PORT`: HTTP port, default `8765`.
- Local launch example: `python backend/server.py --host 127.0.0.1 --port 8765`.
- Server launch example: set `INTERCONNECT_HOST=0.0.0.0` behind an internal reverse proxy and restrict access at the proxy or firewall.

## Data Paths

- `data/projects.json`: saved project intake records and evaluation snapshots.
- `data/local_identity.json`: local anonymous identity used until account login is introduced.
- `data/station_memory.json`: versioned station memory records, including aliases, context corrections, reusable outlines, owner metadata, and provenance.
- `data/admin_station_outlines.json`: shared administrator station-outline records, separate from user project data.
- `frontend/schematic/user_geometry.json`: user/project schematic geometry.
- `exports/`: generated formal reports, score details, snapshots, and PDFs.
- `frontend/schematic/exports/`: generated schematic PNG files.

Back up `data/`, `exports/`, and `frontend/schematic/user_geometry.json` before migration.

## Secrets And API Keys

- `AMAP_JS_KEY`: GaoDe JavaScript key injected into the schematic page.
- `AMAP_SECURITY_CODE`: GaoDe security code injected with the key.
- `OPENAI_API_KEY`: optional model/report capability key.
- `INTERCONNECT_ACCOUNT_MODE`: defaults to `local_anonymous`; set a non-anonymous mode with `INTERCONNECT_ACCOUNT_ID` for local account-owner validation.
- `INTERCONNECT_SECRET_KEY`: required for real server account mode; missing secrets are reported as deployment validation warnings.
- `GENERATED_IMAGE_PROVIDER`: `disabled` by default. Use `local` for a deterministic served artifact path during deployment validation.
- `GENERATED_IMAGE_API_ENABLED=1`: optional flag for provider enablement.
- `INTERCONNECT_EXPORT_PDF=1` or `EXPORT_PDF=1`: optional report PDF conversion.

When generated images are disabled, `POST /api/generated-images` returns a structured `not_configured` response. With `GENERATED_IMAGE_PROVIDER=local`, it writes a served SVG artifact under `exports/generated-images/`. A configured provider without a local adapter returns structured `provider_failure` without touching schematic PNG exports.

## Capability Endpoints

- `GET /api/capabilities`: generated image, account, admin outline, and deployment status.
- `GET /api/identity`: local anonymous identity contract.
- `GET/POST /api/station-memory`: station memory listing and save flow.
- `POST /api/station-memory/apply`: apply station memory to project fields and schematic geometry with immutable source snapshot metadata.
- `GET/POST /api/admin/station-outlines`: shared administrator station-outline storage.
- `POST /api/admin/station-outlines/apply`: apply an administrator outline to project geometry with snapshot source metadata.
- `POST /api/ownership/migrate`: migrate an anonymous saved project record to the active local account owner while keeping the stable project id.

## Migration Checklist

- Copy runtime files and install dependencies.
- Copy `data/`, `exports/`, and schematic geometry/export folders.
- Configure `INTERCONNECT_HOST`, `INTERCONNECT_PORT`, `AMAP_JS_KEY`, `AMAP_SECURITY_CODE`, account mode/secrets, generated-image provider, and optional `OPENAI_API_KEY`.
- Verify `/api/health`, `/api/capabilities`, `/api/bootstrap`, `/api/evaluate`, `/api/export`, and `/schematic/index.html`.
- Confirm `/api/capabilities` reports deployment validation `ok: true` or only accepted warnings.
- Confirm the server process has write permission to `data/`, `exports/`, `exports/generated-images/`, and `frontend/schematic/exports/`.
