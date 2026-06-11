## Why

The feedback lists generated-image API, user accounts, and server migration as desired platform work. The current implementation mainly exposes placeholders and local anonymous identity, which is useful for MVP safety but does not complete those user-facing platform capabilities.

## What Changes

- Define the next implementation step from placeholders to configurable generated-image provider integration.
- Add account/ownership behavior that can run locally while preparing for server deployment.
- Make server migration operational rather than documentation-only: startup config, data/export paths, secret checks, and capability status must be testable.
- Preserve local anonymous usage when account or image providers are disabled.

## Capabilities

### New Capabilities

### Modified Capabilities

- `platform-readiness`: Expand generated-image, account identity, and server migration requirements from placeholder contracts to configurable integration readiness.

## Impact

- Backend capability flags, generated-image endpoint, identity/project ownership handling, and deployment config.
- Frontend disabled/enabled states for image generation and account status.
- Data migration for anonymous local projects to owned project records.
- Deployment scripts and server validation tests.
