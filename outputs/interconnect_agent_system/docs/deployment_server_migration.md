# Deployment And Server Migration Notes

This delivery runs as a local HTTP service and keeps mutable data on disk. Use this note when moving it from a workstation to a shared server.

## Runtime

- Python runtime: use the bundled Python in Codex or install Python 3.11+.
- Node runtime: required for schematic PNG export through `frontend/schematic/export_current_view.cjs`.
- Browser runtime: Chrome or Microsoft Edge must be installed on the server for PNG capture.
- Python packages: install `requirements-server.txt`; optional Word, LibreOffice, or PyMuPDF improves DOCX to PDF conversion. If none is available, the service writes a minimal PDF fallback so export links remain stable.

## Host And Port

- `HOST`: bind address, default `127.0.0.1`.
- `PORT`: HTTP port, default `8765`.
- Local launch example: `python backend/server.py --host 127.0.0.1 --port 8765`.
- Server launch example: set `HOST=0.0.0.0` behind an internal reverse proxy and restrict access at the proxy or firewall.

## Data Paths

- `data/projects.json`: saved project intake records and evaluation snapshots.
- `data/local_identity.json`: local anonymous identity used until account login is introduced.
- `data/admin_station_outlines.json`: shared administrator station-outline records, separate from user project data.
- `frontend/schematic/user_geometry.json`: user/project schematic geometry.
- `exports/`: generated formal reports, score details, snapshots, and PDFs.
- `frontend/schematic/exports/`: generated schematic PNG files.

Back up `data/`, `exports/`, and `frontend/schematic/user_geometry.json` before migration.

## Secrets And API Keys

- `AMAP_JS_KEY`: GaoDe JavaScript key injected into the schematic page.
- `AMAP_SECURITY_CODE`: GaoDe security code injected with the key.
- `OPENAI_API_KEY`: optional model/report capability key.
- `GENERATED_IMAGE_API_ENABLED=1`: optional flag for future generated-image API enablement.

When `GENERATED_IMAGE_API_ENABLED` or `OPENAI_API_KEY` is missing, `POST /api/generated-images` returns a structured `not_configured` response instead of failing opaquely.

## Capability Endpoints

- `GET /api/capabilities`: generated image, account, admin outline, and deployment status.
- `GET /api/identity`: local anonymous identity contract.
- `GET/POST /api/admin/station-outlines`: shared administrator station-outline storage.
- `POST /api/admin/station-outlines/apply`: apply an administrator outline to project geometry with snapshot source metadata.

## Migration Checklist

- Copy runtime files and install dependencies.
- Copy `data/`, `exports/`, and schematic geometry/export folders.
- Configure `HOST`, `PORT`, `AMAP_JS_KEY`, `AMAP_SECURITY_CODE`, and optional `OPENAI_API_KEY`.
- Verify `/api/health`, `/api/capabilities`, `/api/bootstrap`, `/api/evaluate`, `/api/export`, and `/schematic/index.html`.
- Confirm the server process has write permission to `data/`, `exports/`, and `frontend/schematic/exports/`.
