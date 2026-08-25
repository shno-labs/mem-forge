# ADR 0029: Manage local collection as an operating-system user service

## Status

Accepted

## Context

Local Repository, browser-backed Jira, internal GitHub, and Teams collection
must execute on the source owner's machine. The original daemon interface,
`memforge adapter daemon run`, correctly kept collection ownership local but ran
in the foreground. A user who wanted login startup and restart-on-failure had to
write a launchd or systemd definition outside MemForge.

That exposed an operating-system implementation detail as product setup. It
also encouraged users to place API tokens in shell scripts or service unit
environment fields. Package installation alone cannot safely start the daemon:
the target, user credential, and consent to create a login service are not yet
available.

## Decision

MemForge owns local-daemon user-service setup behind the `memforge daemon`
interface.

- `memforge setup` configures or reuses the active target, obtains the Cloud
  token when required, verifies target health, installs the user service, starts
  it, and checks the server-observed heartbeat.
- `memforge daemon install`, `status`, `start`, `stop`, `restart`, `logs`, and
  `uninstall` are the non-interactive lifecycle surface.
- macOS uses a per-user LaunchAgent in `~/Library/LaunchAgents`; Linux uses a
  systemd user unit in `~/.config/systemd/user`. Neither path requires root.
- The native definition directly executes the installed `memforge` entrypoint
  with a hidden service-runtime command. It does not invoke a shell and contains
  no bearer token.
- The exact target URL is stored in a mode-`0600` daemon config. A Cloud bearer
  token is stored only through the operating-system keyring and is loaded by the
  service runtime immediately before the daemon loop starts. Ordinary CLI calls
  may reuse that credential only when their resolved target URL matches exactly.
- launchd stdout and stderr files are created with mode `0600`; systemd uses the
  per-user journal.
- The foreground `memforge adapter daemon run` and one-shot `once` interfaces
  remain available for development and diagnosis.
- Installation refuses to compete with an already running foreground or
  otherwise unmanaged daemon. A loaded native service with the MemForge service
  identity can be replaced in place for upgrades and migration.
- The server continues to own source schedules and durable jobs. Installing a
  user service adds no daemon-side scheduler or business state.

The user-service module is the seam for platform variation. launchd and systemd
are adapters behind the same install, lifecycle, status, and logs interface.
Unsupported operating systems fail before writing service state.

## Consequences

- A normal user performs one explicit setup step after installing the CLI and
  does not need to understand launchd, systemd, or cron.
- Login startup, restart-on-failure, logs, and uninstall behavior are available
  through one MemForge interface on both supported platforms.
- CLI upgrades keep working through the stable installed entrypoint path. A
  target or credential change is applied by rerunning setup or daemon install.
- Installation depends on a working OS keyring. MemForge fails closed instead
  of writing a Cloud token to a plaintext fallback file.
- Windows service installation is not included in this decision and reports an
  explicit unsupported-platform error.

## References

- [Apple: Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [systemd: systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [Python Packaging User Guide: Installing stand-alone command-line tools](https://packaging.python.org/en/latest/guides/installing-stand-alone-command-line-tools/)
