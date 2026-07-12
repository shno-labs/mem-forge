# Domain Context

## Source synchronization

- **Source Sync Activity** — The user-visible lifecycle of current or recent work to bring one source up to date. It can cover both collection from the source and processing into memories.
- **Collection** — Reading source items and, when required, transferring them from the execution device to MemForge.
- **Processing** — Turning collected source items into stored documents and memories.
- **Progress Snapshot** — The latest trustworthy statement of an activity's phase and measurable progress. It is a current observation, not a history of progress events.
- **Determinate Progress** — Progress with a trustworthy total, presented as completed out of total.
- **Indeterminate Progress** — Progress whose total is not yet knowable, presented without a percentage while still reporting useful counts when available.

## Connector authentication

- **Teams Access Token** — A short-lived bearer credential that authorizes one local Teams collection session against a specific Teams service audience.
- **Teams Browser Session** — A persistent, user-authenticated Teams Web session that can acquire fresh Teams Access Tokens without another visible sign-in while enterprise SSO remains valid.
- **Silent Session Renewal** — Renewal of a Teams Access Token through the Teams Browser Session without presenting authentication UI to the user.
- **Interactive Reauthentication** — A visible Teams Web sign-in required when the Teams Browser Session can no longer renew silently because enterprise SSO, MFA, or access policy requires user interaction.
