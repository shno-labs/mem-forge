# GitHub Repository remote scope

## Decision

A GitHub Repository source always reads a configured remote GitHub or GitHub Enterprise repository. Repository Access controls where that remote request executes:

- `cloud_pull`: MemForge Cloud calls GitHub with cloud-managed access.
- `local_push`: the source owner's daemon calls GitHub with the machine's `gh` session, VPN, and network access, then uploads the selected files.

`local_push` is not a local-clone source. GitHub Repository configuration has no daemon-side `repo_path` or folder picker. Local filesystem selection belongs only to the Local Repository (`local_markdown`) source type.

## Scope contract

GitHub Repository scope has three ordered filters:

1. `include_paths`: empty means the entire repository; otherwise it is an allow-list of remote folders or files.
2. `exclude_paths`: an optional deny-list of remote folders or files. Exclusion wins over inclusion and covers descendants. A child below an excluded path cannot be re-included.
3. `include_extensions`: the supported file-extension filter.

Paths are repository-relative, slash-normalized, reject `..`, and have one identity regardless of whether the tree API returns a folder with a trailing slash. Redundant descendants under an already-selected ancestor are collapsed before storage.

The same scope contract applies to cloud discovery, daemon preview, daemon upload, package validation, and local adapter counting. There is no source-type route fallback or compatibility bridge.

## UX

The normal flow is exceptions-first:

1. Show the verified remote repository, ref, and eligible file count.
2. Default to **Sync all supported files in this repository**.
3. Show confirmed exclusions as removable path chips and provide **Choose exclusions**.
4. Put **Sync only selected folders instead** behind a disclosure for allow-list use cases.
5. Use the same remote repository tree picker for both actions. It is loaded through Cloud for `cloud_pull` and through the daemon for `local_push`; the visible scope experience is otherwise identical.
6. Show the effective supported-file count and the matching remote paths while the user edits scope.

Folder names such as `archived`, `deprecated`, or `outdated` may be presented as review suggestions, but are never excluded automatically.

## Migration

Remove `repo_path` from the GitHub Repository schema, admin UI, local-agent job contract, daemon profile construction, and tests. Coordinated one-time SQLite and HANA migrations remove the obsolete key from persisted source config, and new API writes reject it. Do not keep a local-clone branch or fallback.

## Extensibility

Future remote repository connectors can reuse the Base Scope, Exclusion, and Effective Scope concepts. Connector-specific access and tree-fetch implementations stay behind the connector boundary; selection semantics and UI wording remain shared.
