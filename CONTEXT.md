# Domain Context

## Source synchronization

- **Source Lifecycle** — Whether a configured source is active or paused. Lifecycle is independent of where collection executes and whether the current device can perform that collection.
- **Local Execution** — Collection work that must run through the source owner's MemForge daemon on a user-controlled device.
- **Device Readiness** — Whether the source owner's local daemon is recently connected and able to accept collection work.
- **Connection Readiness** — Whether a source-specific connection dependency, such as an authenticated browser session, is usable or requires user action.
- **Local Source Readiness** — The user-facing result derived from Device Readiness and Connection Readiness for a source that uses Local Execution. It never replaces Source Lifecycle.
- **Source Readiness** — The compact source-row outcome derived from execution location, Device Readiness when collection is local, and Connection Readiness when the connector exposes it.
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
