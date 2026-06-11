## Why

The feedback says report export still fails for users, report format should align with the old version, and content hierarchy needs improvement. Existing specs cover basic export links and section order, but the remaining gap is stronger acceptance: export must be reliable in the browser, the DOCX must visibly resemble the agreed reference structure, and evidence such as客流、古城保护、安全、轨保 must be cited without invented conclusions.

## What Changes

- Strengthen report export acceptance so user-visible export/download flows are verified end to end.
- Require DOCX/report structure alignment beyond section order, including heading hierarchy, key tables/blocks, and non-empty evidence sections.
- Require old-city, safety, and rail-protection content to use available authoritative data or be clearly marked for manual verification.
- Add a compact export QA summary artifact or verification output for sample projects.
- Keep PDF optional when the local runtime cannot generate it, but make DOCX and evidence snapshot mandatory.

## Capabilities

### New Capabilities

### Modified Capabilities

- `report-export-content-quality`: Tighten export reliability, visual/structural report alignment, and evidence-source requirements.

## Impact

- Backend report generation and export metadata.
- Frontend export/download UI.
- Report builders in `backend/research_agent.py` and `backend/server.py`.
- Verification scripts for DOCX structure, browser download links, and evidence wording.
- Documentation of export runtime limitations.
