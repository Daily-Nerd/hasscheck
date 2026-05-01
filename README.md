# HassCheck

[![CI](https://github.com/Daily-Nerd/hasscheck/actions/workflows/ci.yml/badge.svg)](https://github.com/Daily-Nerd/hasscheck/actions/workflows/ci.yml)

HassCheck is an **unofficial** CLI for Home Assistant community integration maintainers.

It checks custom integration repositories for sourced HA/HACS quality signals and produces explainable, actionable reports.

```text
Security Review: Not performed
Official HA Tier: Not assigned
HACS Acceptance: Not guaranteed
```

HassCheck is not affiliated with Home Assistant, HACS, Nabu Casa, or the Open Home Foundation. It does **not** certify integrations, prove that an integration is safe, or guarantee HACS acceptance.

## What HassCheck does

HassCheck turns scattered Home Assistant and HACS expectations into local checks that are:

- **Sourced** — every finding carries a source URL and checked date.
- **Explainable** — each rule has a stable ID, version, title, reason, and fix suggestion.
- **Actionable** — output points maintainers toward concrete next fixes.
- **Machine-readable** — JSON output is the stable contract for future GitHub Actions, badges, hosted reports, and tooling.

HassCheck starts as a local CLI. Public badges, hosted reports, and any future hub should be opt-in only.

## Current status

- **Latest release:** v0.7.0 — opt-in hosted reports via GitHub OIDC
- **Current development target:** v0.8.0 — license, packaging metadata, and schema-versioning policy (in progress)

v0.6.0 includes:

- GitHub Action (`uses: Daily-Nerd/hasscheck@v0.6.0`) with PR comment, JSON artifact upload, and opt-in badge artifact
- Typer CLI with `check`, `explain`, `schema`, `scaffold`, and `badge` commands
- Rich terminal output with per-finding fix suggestions
- `scaffold github-action` — generate a GitHub Actions CI workflow
- `scaffold diagnostics` — generate a `diagnostics.py` starter with redaction helpers
- `scaffold repairs` — generate a `repairs.py` starter with `ConfirmRepairFlow` skeleton
- Applicability-aware scaffold refusal (respects `hasscheck.yaml` flags)
- `hasscheck badge` — opt-in shields.io endpoint JSON for per-category quality signals
- Pydantic JSON report schema (stable, additive-only versioning)
- Rule IDs and rule versions
- Source links and source timestamps
- Applicability-aware statuses
- Per-rule config overrides via `hasscheck.yaml`
- Project applicability context via `hasscheck.yaml`
- Example good and partial integration fixtures
- Pytest coverage for the current rule set

## GitHub Action

Add HassCheck to any integration repository's CI with one step:

```yaml
name: HassCheck

on:
  pull_request:
  push:
    branches: [main]

jobs:
  hasscheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Daily-Nerd/hasscheck@v0.7.0
        with:
          comment-pr: true
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Inputs:**

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Repository path to inspect |
| `no-config` | `false` | Ignore `hasscheck.yaml` if present |
| `comment-pr` | `false` | Post findings as a PR comment |
| `github-token` | `''` | Required when `comment-pr: true` |
| `emit-badges` | `false` | Generate shields.io badge JSON and upload as artifact |
| `badges-out-dir` | `badges` | Directory for badge JSON when `emit-badges: 'true'` |
| `emit-publish` | `false` | Publish the report to a hosted HassCheck service. Requires workflow `permissions: id-token: write` |
| `publish-endpoint` | `https://hasscheck.io` | Publish endpoint URL when `emit-publish: 'true'` |

**Outputs:** `exit-code` — `0` when no FAIL findings, `1` when one or more FAIL findings.

The action uploads `hasscheck-report.json` as a build artifact on every run.

## Badges (opt-in)

HassCheck can generate [shields.io](https://shields.io) endpoint JSON files for embedding specific quality signals in your README. Badges are **opt-in only** and show specific signals — not vague trust claims.

### Generate locally

```bash
hasscheck badge --path . --out-dir badges/
```

This writes per-category JSON files and a `manifest.json` to `badges/`. Commit these files to your repo.

### Generate in CI

Add `emit-badges: 'true'` to your HassCheck action step:

```yaml
- uses: Daily-Nerd/hasscheck@v0.7.0
  with:
    emit-badges: 'true'
    badges-out-dir: 'badges'
```

This uploads a `hasscheck-badges` artifact. To embed in your README, publish the JSON files somewhere publicly accessible (e.g. committed to your repo or hosted on GitHub Pages).

### Embed in README

Replace `OWNER/REPO/main` with your repository path:

```markdown
![HACS Structure](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/hacs_structure.json)
![Config Flow](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/modern_ha_patterns.json)
![Diagnostics](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/diagnostics_repairs.json)
![Tests & CI](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/tests_ci.json)
![HassCheck](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/hasscheck.json)
```

Badges show the current state of your integration: `Passing`, `Partial`, or `Issues`. For `Config Flow` and `Diagnostics`, suffixes are `Present` or `Missing`.

> HassCheck is unofficial and not affiliated with Home Assistant, HACS, or Nabu Casa.
> Security Review: Not performed. HACS Acceptance: Not guaranteed.

## Install for local development

This repository uses [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

Run the CLI without installing globally:

```bash
.venv/bin/python -m hasscheck --help
```

## Commands

### Check a repository

```bash
.venv/bin/python -m hasscheck check --path .
```

### Emit JSON

```bash
.venv/bin/python -m hasscheck check --path . --format json
```

### Print the JSON schema

```bash
.venv/bin/python -m hasscheck schema
```

### Skip config file

```bash
.venv/bin/python -m hasscheck check --path . --no-config
```

### Explain a rule

```bash
.venv/bin/python -m hasscheck explain manifest.domain.exists
```

### Scaffold a GitHub Actions workflow

```bash
.venv/bin/python -m hasscheck scaffold github-action --path .
```

### Scaffold a diagnostics.py starter

```bash
.venv/bin/python -m hasscheck scaffold diagnostics --path .
```

### Scaffold a repairs.py starter

```bash
.venv/bin/python -m hasscheck scaffold repairs --path .
```

Use `--dry-run` to preview without writing, `--force` to overwrite an existing file.

## Configuration

HassCheck reads `hasscheck.yaml` at the repository root when present.

The file supports two separate kinds of user intent:

1. **Project applicability context** — declare project-level facts once, so selected rules can return `not_applicable` without repetitive per-rule overrides.
2. **Per-rule overrides** — mark specific RECOMMENDED rules as `not_applicable` or `manual_review` with a written reason.

```yaml
# hasscheck.yaml
schema_version: "0.3.0"

applicability:
  supports_diagnostics: false
  has_user_fixable_repairs: false
  uses_config_flow: false

rules:
  repo.license.exists:
    status: manual_review
    reason: License decision pending before public release.
```

**Rules for project applicability:**

- Flags only explain intentionally missing optional signals.
- Natural `pass` findings still win — existing files are not hidden by stale config.
- Correctness failures stay locked. For example, `uses_config_flow: false` does not hide a `config_flow.py` / `manifest.json` mismatch.
- Applied decisions are disclosed in JSON as `summary.applicability_applied` and marked in terminal findings with `(config)`.

**Rules for overrides:**

- `status` must be `not_applicable` or `manual_review` — you cannot force a finding to `pass`.
- `reason` is required — it is the audit trail.
- REQUIRED rules (e.g. `manifest.exists`) cannot be overridden.
- Run `hasscheck explain <rule-id>` to check if a rule is overridable.
- Use `--no-config` to ignore `hasscheck.yaml` (useful for CI debugging).

See `hasscheck.example.yaml` in this repository for a full annotated example.
See `docs/architecture/config-file.md` and `docs/architecture/project-applicability-context.md` for the design rationale.

## Finding statuses

HassCheck findings use explicit statuses instead of a single global certification score.

| Status | Meaning |
| --- | --- |
| `pass` | The signal was found. |
| `warn` | The signal is missing or incomplete, but should not block every project. |
| `fail` | The repository has an internally inconsistent or required metadata problem. |
| `not_applicable` | The rule does not apply yet or cannot be evaluated from current context. |
| `manual_review` | Human judgment is needed. |

## Example terminal output

```text
HassCheck Summary

Diagnostics/Repairs: 2 / 2
Docs/Support: 1 / 1
HACS Structure: 3 / 3
Maintenance Signals: 1 / 1
Manifest Metadata: 7 / 7
Modern HA Patterns: 2 / 2
Tests/CI: 2 / 2

Overall: Informational only
Security Review: Not performed
Official HA Tier: Not assigned
HACS Acceptance: Not guaranteed
```

The exact category order may change as rules evolve. The JSON schema is the durable contract.

## Current rule set

### HACS structure

| Rule ID | Signal |
| --- | --- |
| `hacs.custom_components.exists` | Repository has `custom_components/`. |
| `hacs.file.parseable` | Repository has parseable `hacs.json`. |
| `brand.icon.exists` | Integration has `custom_components/<domain>/brand/icon.png`. |

### Manifest metadata

| Rule ID | Signal |
| --- | --- |
| `manifest.exists` | Integration has `manifest.json`. |
| `manifest.domain.exists` | Manifest defines `domain`. |
| `manifest.domain.matches_directory` | Manifest `domain` matches the integration directory name. |
| `manifest.name.exists` | Manifest defines `name`. |
| `manifest.version.exists` | Manifest defines `version`. |
| `manifest.documentation.exists` | Manifest defines `documentation`. |
| `manifest.issue_tracker.exists` | Manifest defines `issue_tracker`. |
| `manifest.codeowners.exists` | Manifest defines non-empty `codeowners`. |
| `manifest.iot_class.exists` | Manifest declares `iot_class`. |
| `manifest.iot_class.valid` | Manifest `iot_class` is a recognized value. |
| `manifest.integration_type.exists` | Manifest declares `integration_type`. |
| `manifest.integration_type.valid` | Manifest `integration_type` is a recognized value. |

### Modern Home Assistant patterns

| Rule ID | Signal |
| --- | --- |
| `config_flow.file.exists` | Integration has `config_flow.py`. |
| `config_flow.manifest_flag_consistent` | `config_flow.py` and manifest `config_flow: true` agree. |
| `config_flow.user_step.exists` | `config_flow.py` defines `async_step_user` (AST inspection). |

### Diagnostics and repairs

| Rule ID | Signal |
| --- | --- |
| `diagnostics.file.exists` | Integration has `diagnostics.py`. |
| `diagnostics.redaction.used` | `diagnostics.py` uses `async_redact_data` or a local redaction helper (AST inspection). |
| `repairs.file.exists` | Integration has `repairs.py`. |

### Docs and maintenance

| Rule ID | Signal |
| --- | --- |
| `docs.readme.exists` | Repository has a README. |
| `repo.license.exists` | Repository has a license file. |

### Tests and CI

| Rule ID | Signal |
| --- | --- |
| `tests.folder.exists` | Repository has `tests/`. |
| `ci.github_actions.exists` | Repository has `.github/workflows/*.yml` or `.yaml`. |

## JSON report contract

JSON output includes:

- `schema_version`
- tool metadata
- project metadata
- ruleset metadata
- category summaries
- config disclosure summaries (`overrides_applied` and `applicability_applied`)
- findings with rule IDs, rule versions, statuses, applicability, source URLs, and fix suggestions

Example:

```bash
.venv/bin/python -m hasscheck check --path examples/good_integration --format json
```

Use `hasscheck schema` to inspect the full report schema.

## Development

Run tests:

```bash
.venv/bin/python -m pytest -q
```

Run HassCheck against the good fixture:

```bash
.venv/bin/python -m hasscheck check --path examples/good_integration
```

Run HassCheck against the current repository:

```bash
.venv/bin/python -m hasscheck check --path .
```

## Release process

Releases are source-only GitHub Releases created from version tags.

Before tagging a new version, make sure all version declarations match `pyproject.toml`:

```bash
.venv/bin/python scripts/check_version.py
```

Then run the release checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m hasscheck check --path examples/good_integration
.venv/bin/python -m hasscheck check --path examples/good_integration --format json
.venv/bin/python -m hasscheck schema
.venv/bin/python -m hasscheck explain manifest.domain.exists
```

Then create and push an annotated version tag:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — short release summary"
git push origin vX.Y.Z
```

Pushing a tag that matches `v*.*.*` triggers the release workflow. The workflow creates a GitHub Release for that tag with generated notes and a source-only artifact notice.

This workflow does **not** publish to PyPI and does **not** attach built package artifacts. PyPI publishing is a separate release step.

## Non-goals

HassCheck does not attempt:

- Security certification
- Official Home Assistant quality tier assignment
- HACS acceptance guarantees
- Runtime testing against physical devices
- Full semantic correctness checks
- Public crawling or ranking of random repositories
- Automatic PRs to third-party repos
- Source-code auto-detection of project applicability
- Multi-integration repository support

## Philosophy

HassCheck should say:

```text
Automated checks found these quality signals.
```

Not:

```text
This integration is certified, safe, approved, or officially ready.
```
