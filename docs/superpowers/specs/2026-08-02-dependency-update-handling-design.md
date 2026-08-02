# Dependency update handling

## Problem

Dependency updates currently arrive two ways: Dependabot opens a PR per
outdated `pip` package on a weekly schedule, and nothing keeps `poetry.lock`
itself in sync with what those version bumps imply for the full dependency
graph. There's no cooldown protecting against very-freshly-published
releases (a supply-chain risk window), and routine non-security bumps create
Dependabot PR noise.

Goal: Dependabot should only raise PRs for security fixes; routine version
bumps should instead happen in one batched weekly PR that regenerates the
lock file, with a safety cooldown so packages published in the last 7 days
aren't pulled in automatically.

Note: this repo manages dependencies with **Poetry**, not uv (despite the
branch name `better-uv-handling`). The original ask referenced uv's
`exclude-newer` config; the Poetry equivalent used here is
`solver.min-release-age` (added in Poetry 2.4), which requires a release to
be at least N days old before Poetry's resolver will consider it.

This work spans two repositories:

- **`calysto/maintainer_tools`** (forked as `blink1073/maintainer_tools`,
  branch `poetry-lock-upgrade` already created) — reusable GitHub Actions
  for Calysto packages, consumed via the `v1` floating tag. oct2py already
  depends on several of its actions (`base-setup`, `pre-commit-autoupdate`,
  `release`, etc.).
- **`oct2py`** (this repo, branch `better-uv-handling`) — the consumer.

## Design

### 1. New shared action: `maintainer_tools/actions/poetry-lock-update`

Modeled directly on the existing `actions/pre-commit-autoupdate` action
(same repo) — same job shape: run an updater with a cooldown, diff, open a
PR via a GitHub App token. Assumes `base-setup` already ran in the calling
workflow (Poetry is installed), matching the convention already documented
in `CLAUDE.md` for the `release` action.

`actions/poetry-lock-update/action.yml`:

**Inputs**

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `app-id` | No | `""` | GitHub App ID for authenticated pushes. Falls back to `github.token`. |
| `app-private-key` | No | `""` | GitHub App private key for authenticated pushes. |
| `min-release-age-days` | No | `"7"` | Minimum release age in days before Poetry's resolver will consider a version (`POETRY_SOLVER_MIN_RELEASE_AGE`). |
| `branch` | No | `"poetry-lock-update"` | Branch name for the update pull request. |
| `labels` | No | `"maintenance"` | Labels to apply to the pull request. |
| `dry-run` | No | `"false"` | If `"true"`, passes `--dry-run` to `gh pr create`. |

**Steps**

1. Generate app token (`actions/create-github-app-token@v3`) if `app-id`/`app-private-key` given.
2. Run `poetry update --no-interaction` with `POETRY_SOLVER_MIN_RELEASE_AGE` set from `min-release-age-days`.
3. If `git diff --quiet` on `poetry.lock`, exit early — no PR.
4. Otherwise: parse old vs. new `poetry.lock` via a new `diff_lock.py` script (uses `tomllib` to build `name -> version` maps for each side and diff them — TOML, not YAML, so this can't reuse `pre-commit-autoupdate`'s `parse_diff.sh`), building an "Updated packages" list (`name: old -> new`).
5. Commit `poetry.lock` to a new branch (`<branch>-<random suffix>`), push, and `gh pr create` with title `chore: update poetry.lock`, the generated body, and the given labels — same commit/push/PR mechanics as `pre-commit-autoupdate`'s `Create pull request` step.

**Supporting files**

- `actions/poetry-lock-update/diff_lock.py` — the lock-diff parser.
- `actions/poetry-lock-update/test_diff_lock.py` — unit test, following the style of `actions/pre-commit-autoupdate/test_parse_diff.sh` (fixture old/new TOML snippets, assert the generated markdown lines).

**Wiring into the rest of `maintainer_tools`**

- `README.md` — new `### poetry-lock-update` section, following the existing per-action doc format (inputs table + usage examples), inserted alongside `pre-commit-autoupdate`.
- `CLAUDE.md` — add a bullet to the Actions list under Architecture.
- `.github/workflows/tests.yml`:
  - `test_scripts` job — add a `Test diff_lock.py` step.
  - New `test_poetry_lock_update` job — mirrors `test_pre_commit_autoupdate` (calls the action with `dry-run: "true"`), included in `tests_check`'s `needs`.

**PR target**: `gh pr create --repo Calysto/maintainer_tools --head blink1073:poetry-lock-upgrade --base main`, per this repo's `CLAUDE.md`.

### 2. oct2py: Dependabot security-only for `pip`

Add `open-pull-requests-limit: 0` to the existing `pip` entry in
`.github/dependabot.yml`. This is GitHub's documented mechanism for
disabling routine version-update PRs for an ecosystem while leaving
security-update PRs unaffected (security updates ignore this limit). The
`github-actions` entry is untouched.

### 3. oct2py: weekly lock-update workflow

New `.github/workflows/lock-update.yml`:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * 1"  # Every Monday at 6am

jobs:
  lock-update:
    runs-on: ubuntu-latest
    environment: release
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: calysto/maintainer_tools/actions/base-setup@v1
      - uses: calysto/maintainer_tools/actions/poetry-lock-update@v1
        with:
          app-id: ${{ vars.APP_ID }}
          app-private-key: ${{ secrets.APP_PRIVATE_KEY }}
```

(`vars.APP_ID` / `secrets.APP_PRIVATE_KEY` are the same GitHub App already
used by `release.yml` and `pre-commit-autoupdate.yml` in this repo.)

### 4. No `pyproject.toml` change in either repo

`solver.min-release-age` is a Poetry CLI/config setting, not a
`pyproject.toml` key — it's applied purely via the env var inside the
shared action.

## Sequencing

1. Land `poetry-lock-update` in `maintainer_tools` first: open the PR
   (`blink1073:poetry-lock-upgrade` → `Calysto/maintainer_tools:main`), get
   it merged, and let the `v1` floating tag move to it (per the existing
   `update-v1-tag` release job).
2. Then open the `oct2py` PR with the dependabot change and the new
   `lock-update.yml`, which references `calysto/maintainer_tools/actions/poetry-lock-update@v1`
   directly — no branch-pinned placeholder to clean up later.

## Out of scope

- Migrating `oct2py` from Poetry to uv (confirmed with user: repo stays on
  Poetry for now).
- Applying the release-age cooldown to regular CI installs (`tests.yml` in
  either repo) — those install from the committed lock file and don't
  re-resolve, so it would be a no-op there.
- A Dependabot `cooldown` block for `pip` in oct2py — moot once
  `open-pull-requests-limit: 0` suppresses version-update PRs entirely.
