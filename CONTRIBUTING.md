# Contributing to SA EzyCheck

Contributions - bug reports, feature requests, and pull requests - are welcome.

## Quality bar

This integration targets the **Platinum tier of the Home Assistant Integration Quality
Scale**. Contributions are expected to conform to it, not just pass CI:

- [Integration Quality Scale](https://contributors.home-assistant.io/core/quality-scale/) and its
  rule pages (each rule page name matches the rule name used in the audit)
- This project's own rule-by-rule audit: <!-- FILL: link to the audit issue once it exists -->

If a change touches entity behavior, config flow, or diagnostics, check whether it affects any rule
the audit already addressed before assuming it's fine.

## Reporting bugs and requesting features

Use the issue templates rather than a blank issue:

- **Bug report** - fill out the [bug report form](https://github.com/dale-sharp/sa-ezycheck-homeassistant/issues/new?template=bug_report.yml). It asks for System Health details, reproduction steps, and debug logs - these aren't optional extras, they're what makes a bug reproducible.
- **Feature request** - fill out the [feature request form](https://github.com/dale-sharp/sa-ezycheck-homeassistant/issues/new?template=feature_request.yml).

## Development setup

This project's dev/test dependencies (via `pytest-homeassistant-custom-component`) require Linux:
Home Assistant's own runner unconditionally imports POSIX-only stdlib modules (`fcntl`, `resource`)
that don't exist on Windows, at any Python version. **The devcontainer in `.devcontainer/` is the only supported
way to run `uv sync`/`pytest` locally.**

```bash
git clone https://github.com/dale-sharp/sa-ezycheck-homeassistant.git
cd sa-ezycheck-homeassistant
```

Open the folder in an editor with Dev Containers support (VS Code's "Reopen in Container", JetBrains
Gateway), or drive it directly with the [devcontainer CLI](https://github.com/devcontainers/cli):

```bash
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . -- uv run pytest --cov=custom_components.sa_ezycheck --cov-report=term-missing
```

**If your container engine is Podman on Windows** (not Docker Desktop): `docker.exe`'s default context
points at Docker Desktop, not Podman. Set `DOCKER_CONTEXT=default` before any `docker`/`devcontainer`
command (e.g. `export DOCKER_CONTEXT=default` in your shell), or pass `--docker-path` pointing at your
`podman` binary. Otherwise the tooling silently tries to reach a daemon that isn't running.

[`uv`](https://docs.astral.sh/uv/) manages the environment and all dependencies (dev and runtime) from
`pyproject.toml`/`uv.lock` inside the container - there's no separate `pip install -r requirements.txt`
step.

## Before opening a pull request

Run these locally (inside the devcontainer) - they're exactly what CI runs, so a clean local run means a
clean CI run:

```bash
uv run pytest --cov=custom_components.sa_ezycheck --cov-report=term-missing
uv run ruff format .
uv run ruff check .
uv run ty check
```

- **Coverage:** this project starts at 100% on every module and new code is expected to keep it there: a new project has no reason to carry untested code. The CI gates are minimums, not the target: at least 95% overall and no module below ~90%. Both are enforced in CI
  (`.github/workflows/lint.yml`'s `pytest` job): the 95% overall floor via `fail_under` in
  `pyproject.toml`, and the per-module floor via `scripts/check_coverage_floor.py` against the
  `coverage.json` report - coverage.py has no built-in way to gate an individual file's percentage.
  If your change drops a module below the floor, add a real test for the new code path; don't accept
  the regression just because it is still above the minimum.
- **If `ruff check .` shows only `EXE002` findings inside the devcontainer** on a Windows host: this
  is a known, harmless local artifact. The Windows-to-WSL2 bind mount reports every file as mode
  `0777`, regardless of git's tracked (non-executable) permissions, and it never appears in CI. Run
  `uv run ruff check . --config .devcontainer/ruff-devcontainer.toml` locally to filter it out; that
  override file is never used by CI, so it can't mask a real finding there.
- **Paste the actual output of pytest** (not just pass/fail) into your PR's test plan, regardless of
  CI passing. CI passing doesn't replace showing your local run.
- **Version bumps.** PRs that change `custom_components/sa_ezycheck/` bump the version -
  `manifest.json` + `pyproject.toml` + `uv.lock` (via `uv lock`) - and add a `CHANGELOG.md` entry.
  PRs that only touch repo tooling or docs (`.github/`, `.devcontainer/`, `README.md`, this file,
  etc.) don't need one: none of that is included in the release zip HACS installs, so bumping would
  announce a "new release" with unchanged shipped files. State explicitly in the PR which case
  applies rather than leaving it ambiguous.
- Use the [pull request template](https://github.com/dale-sharp/sa-ezycheck-homeassistant/blob/main/.github/pull_request_template.md);
  its test plan section expects pasted command output, not a checkbox.

## Handling Home Assistant breaking changes

Home Assistant changes quickly, and this integration is distributed outside core, so nobody else
updates it. When a Home Assistant release breaks or deprecates something this integration uses:

1. **Find out what changed and from which version.** Read the release notes and the developer blog
   for the version, and check the deprecation or removal date if one is given.
2. **Decide between a compatibility shim and raising the minimum.**
   - Prefer a **compatibility shim** when old and new can both be supported cheaply and the shim
     is small and tested on both sides. Example (dated, verify before copying): Home Assistant 2026.9
     replaced `voluptuous` with `probatio` in config flows, so `config_flow.py` imports `probatio`
     and falls back to `voluptuous` on older releases, behind `TYPE_CHECKING` so type checking
     follows the new engine.
   - **Raise the minimum Home Assistant version** when the old API is removed, scheduled for
     removal, or the shim would be larger than the change. Example (dated, verify before copying):
     Home Assistant 2026.8 restricted each device to a single config entry and introduced
     `DeviceRegistry.async_get_device_by_identifier` and `async_remove_device`; the old calls were
     deprecated for removal, so the device registry cleanup moved to the new calls and the minimum
     became 2026.8.0.
3. **Keep the declared floor and the test harness consistent.** `pytest-homeassistant-custom-component`
   pins the exact `homeassistant` version the tests run against, so the harness always tests the newest
   release; the floor in `hacs.json` (`homeassistant`) must be a version you have reason to believe
   works. Raise it deliberately and say why. Never lower it without verifying.
4. **Cover the change with tests** on the harness version, including the fallback path for a shim.
5. **Bump the version and add a `CHANGELOG.md` entry** that states what changed in Home Assistant,
   what the integration does now, and the new minimum if it moved. Update the README's requirements.
6. If Home Assistant drops a Python version, move the toolchain (devcontainer, `ruff`/`ty` targets,
   `requires-python`) with it. A stale Python ceiling silently freezes Dependabot's Home Assistant
   updates because no newer release can be resolved.

## Dependabot

`.github/dependabot.yml` groups `homeassistant`, `pytest-homeassistant-custom-component`, `aiohttp`,
`pytest-asyncio` and `pytest` into one update. `pytest-homeassistant-custom-component` pins exact
versions of the others, so bumping any one alone produces an unsatisfiable `uv lock`; grouped, Dependabot
proposes one resolvable update. Home Assistant pins many other packages exactly. Don't enumerate them in
advance: when Dependabot fails to bump one in isolation, add it to the group and note why in the
comment above it.

## License

By contributing, you agree that your contributions will be licensed under this project's
AGPL-3.0-or-later license (see [LICENSE](LICENSE)).
