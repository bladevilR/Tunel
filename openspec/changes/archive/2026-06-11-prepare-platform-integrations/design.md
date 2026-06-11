## Context

The current platform-readiness layer exposes capability flags, a generated-image placeholder, and local anonymous identity. That prevents broken buttons, but it does not yet provide a usable image-generation integration, account ownership, or operational server deployment checks.

## Goals / Non-Goals

**Goals:**

- Keep disabled integrations explicit and safe.
- Add a provider abstraction for generated images that can save generated artifacts and return metadata.
- Introduce minimal local account/owner semantics compatible with future server auth.
- Make server deployment configuration testable.

**Non-Goals:**

- Implement enterprise SSO or multi-tenant RBAC.
- Replace local-first development with mandatory login.
- Guarantee image quality; this change defines integration behavior and artifact handling.

## Decisions

- Keep capability flags as the source of truth for UI availability and endpoint behavior.
- Use an image provider abstraction with a disabled provider and at least one configured provider path. Outputs should be saved and served like other export artifacts.
- Add owner metadata to projects while allowing anonymous local ownership. When accounts are enabled, projects can be associated with a local user/account record.
- Add a deployment validation script that checks host/port, data paths, export paths, API keys, generated-image flags, and account mode before startup or acceptance.

## Risks / Trade-offs

- Account support can balloon quickly. Mitigation: start with ownership and local users, not full permission matrices.
- Image generation can consume external API credits. Mitigation: keep explicit enablement, provider status, and failure reporting.
- Server paths may differ by deployment. Mitigation: centralize config and validate resolved paths at startup.
