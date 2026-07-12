# Local source readiness

Local source rows use one readiness model regardless of connector type. The model keeps source lifecycle, device availability, and connector authentication separate so a new local connector can reuse the existing UI without adding provider-specific presentation code.

## Domain model

| Concept | Question it answers | Examples |
| --- | --- | --- |
| Source Lifecycle | Should this configured source run? | `active`, `paused` |
| Local Execution | Where must collection run? | the source owner's MemForge daemon |
| Device Readiness | Can that daemon accept work now? | online, checking, unavailable |
| Connection Readiness | Can the connector access its upstream system? | ready, sign-in required, account mismatch |
| Local Source Readiness | Can this device collect this source now? | Local sync ready, Local sync unavailable, Sign in required |

Source Lifecycle is always rendered independently. An active source can still be locally unavailable, and a paused source does not become active merely because its daemon is online.

## Wire contract

Every source already exposes its execution contract:

```json
{
  "execution": {
    "kind": "local_agent",
    "operation": "jira_sync",
    "immutable_config_fields": ["sync_mode"]
  }
}
```

A connector with a separately observable connection dependency may additionally expose this provider-neutral status:

```json
{
  "connection_status": {
    "state": "action_required",
    "reason": "authentication"
  }
}
```

`state` is `ready` or `action_required`. `reason` is `authentication`, `identity_conflict`, or `configuration`. The source list must not expose credential values, browser names, principals, raw provider errors, or provider-specific status labels.

Connectors without a separately observable connection dependency omit `connection_status`. For them, an online daemon is sufficient to report local readiness.

## Derivation and precedence

The shared presenter derives one compact badge in this order:

| Condition | Badge | Tone |
| --- | --- | --- |
| Source Lifecycle is paused | no readiness badge | lifecycle badge remains visible |
| daemon query is pending | Checking local sync | muted |
| daemon is offline or its status cannot be read | Local sync unavailable | warning |
| connection reason is `identity_conflict` | Account mismatch | destructive |
| connection requires action | Sign in required | warning |
| connection reason is `configuration` | Finish setup | warning |
| daemon is online and no connection blocker exists | Local sync ready | neutral |

Device availability takes precedence over connection readiness because a stopped daemon cannot perform or repair local collection. Provider-specific recovery instructions belong in Configure, not in the source row.

## Presentation rules

- Render Source Lifecycle and Local Source Readiness as separate siblings next to the source name.
- Never replace `active` or `paused` with `Local sync ready`.
- Do not render healthy provider authentication as another metadata sentence. `Browser session active` and `Teams token active` are implementation details, not user outcomes.
- Show exceptional connection state only through the shared readiness badge.
- Keep technical evidence such as browser profile, Keychain capture time, and principal details inside Configure or a diagnostic surface.
- On narrow screens the badges may wrap after the source name; they must not create a standalone metadata row or displace the primary Sync action.

## Adding a local connector

1. Register its collection path as `execution.kind = local_agent` and give it a daemon operation.
2. If daemon availability is its only runtime dependency, do not add a connection status.
3. If it has a server-observable connection dependency, translate that dependency into the generic `connection_status` contract at the source API boundary.
4. Do not add connector names, auth terminology, colors, or conditional branches to `SourceRow` or the readiness badge.
5. Add the connector to the shared readiness test matrix for online, offline, paused, and any supported connection blocker.

Examples:

| Connector | Local execution | Connection status |
| --- | --- | --- |
| Local Repository | required | omitted |
| GitHub Repository / local push | required | omitted |
| Microsoft Teams | required | omitted while the daemon owns silent token renewal |
| Jira / browser session | required | derived from the stored browser-session status |
| Future authenticated local connector | required | translate its auth state into the generic contract |
