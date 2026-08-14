# Releasing the Python distribution

The public Python distribution is named `mem-forge`. It intentionally keeps the
Python import package and installed command named `memforge`:

| Surface | Name |
| --- | --- |
| PyPI distribution | `mem-forge` |
| Python import | `memforge` |
| Console command | `memforge` |

## Trusted Publisher

PyPI publishing uses GitHub Actions OpenID Connect and stores no PyPI API token
in the repository. Configure one PyPI pending publisher with these exact values:

| Field | Value |
| --- | --- |
| PyPI project | `mem-forge` |
| GitHub owner | `shno-labs` |
| GitHub repository | `mem-forge` |
| Workflow | `publish-pypi.yml` |
| Environment | `pypi` |

The pending publisher does not reserve the project name. Complete the first
release immediately after configuring it.

## Release sequence

1. Update `project.version` in `pyproject.toml` and refresh `uv.lock`.
2. Merge the version change after CI passes.
3. Create a GitHub release whose tag is exactly `mem-forge-v<version>`, for
   example `mem-forge-v0.1.55`.
4. The release workflow builds one wheel and one source distribution, verifies
   their metadata and `memforge` console entry point, and publishes them through
   the `pypi` environment.
5. Verify the public installation from a clean tool environment:

   ```bash
   pipx install mem-forge
   memforge --help
   python -c 'from importlib.metadata import version; print(version("mem-forge"))'
   ```

Plugin tags such as `memforge-memory-v0.1.55` do not match the Python release
tag contract and are rejected by the artifact verifier.
