# athc release

Dev-facing process for cutting an athc release. End-user install behavior lives in [installer.md](installer.md).

## Versioning

- **Scheme**: SemVer (`MAJOR.MINOR.PATCH`). Stay below `1.0.0` until interfaces are committed-to.
- **Source of truth**: `version = "..."` in `pyproject.toml`. Code reads it via `importlib.metadata.version(...)`; never hard-code.

## Release steps

1. Bump `version` in `pyproject.toml`.
2. Add a "What's new in v0.X.0" entry near the top of `config/release/docs/README.txt`.
3. Commit, then tag: `git tag v0.X.0`.
4. Run `packaging/release-build.ps1` to produce `dist/athc-<ver>-setup.exe`.
5. Run `packaging/release-test.ps1` to test it in Windows Sandbox.
6. Distribute the setup.exe.
