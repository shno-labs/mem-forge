# Renew Teams access through a dedicated browser session

Teams collection will treat the OS keychain as the primary cache for a short-lived Teams Access Token and a dedicated persistent Teams Browser Session as the authority for renewing it. The daemon will reuse a valid cached token, attempt Silent Session Renewal in a headless browser when the token is near expiry or rejected, and request Interactive Reauthentication only when the enterprise SAP SSO session, MFA, or Conditional Access requires it. Silent renewal redeems the Teams Web client's existing Microsoft Entra/MSAL refresh token through the Teams first-party client, persists any rotated refresh token back into the dedicated profile, and accepts IC3 or Graph access tokens only after validating their audience and expiry. The path does not register a MemForge OAuth application, copy the user's everyday Chrome profile, or rely on bearer-token cookies alone.

## Consequences

The dedicated browser session must be initialized once through a visible login, stored separately from the user's normal browser profile, serialized across daemon work, and bounded by short launch and capture timeouts. A successful renewal updates the keychain atomically; a failed silent renewal may open one visible authentication window, but concurrent syncs must share that reauthentication attempt.
