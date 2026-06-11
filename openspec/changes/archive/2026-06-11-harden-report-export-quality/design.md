## Context

Previous work added export metadata and formal report sections, but feedback still treats report export and content as not fully acceptable. The current acceptance should move from "files are non-empty" to "a user can download them and the generated report is structurally aligned, readable, and evidence-safe."

## Goals / Non-Goals

**Goals:**

- Verify report export from the browser and backend with served links.
- Enforce legacy-reference alignment at section, heading, and core block level.
- Make evidence limitations visible rather than overclaiming unsupported facts.

**Non-Goals:**

- Build a new Word templating engine unless existing generation cannot satisfy requirements.
- Guarantee PDF output on runtimes that lack a converter.
- Resolve all missing authoritative map layers; the report must mark them correctly when unavailable.

## Decisions

- Maintain DOCX as the mandatory formal-report artifact and treat PDF as optional/runtime-dependent.
- Add structural checks for headings, required evidence phrases, and key sections before declaring export success.
- Prefer deterministic report builders over model-only prose for core sections, with model/research output used as supporting evidence where available.
- Add a user-facing export failure message that names the missing runtime or artifact class.

## Risks / Trade-offs

- Strict report checks can reject otherwise useful drafts. Mitigation: separate blocking checks (missing file, missing section, invented source) from warnings (stylistic polish).
- Visual DOCX QA may be difficult without LibreOffice. Mitigation: require structural DOCX checks locally and document visual QA as a deploy/runtime acceptance step if rendering is unavailable.
- Evidence-safe wording can feel conservative. Mitigation: use clear "manual verification" language and source labels to maintain credibility.
