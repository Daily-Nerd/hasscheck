# Badge architecture (v0.6)

## Overview

`hasscheck badge` writes shields.io endpoint JSON files to a local output
directory. Each file represents one category's aggregate status. The files can
be committed to a repository or hosted on GitHub Pages so shields.io can read
them via a public URL.

Badges are **opt-in only** — never emitted by `hasscheck check` or the GitHub
Action unless the caller explicitly requests them. See ADR 0007 for the policy
rationale.

## Badge schema (shields.io endpoint format)

Each `.json` file follows the
[shields.io endpoint schema](https://shields.io/endpoint):

```json
{
  "cacheSeconds": 300,
  "color": "brightgreen",
  "label": "HACS Structure",
  "message": "Passing",
  "schemaVersion": 1
}
```

Fields are sorted alphabetically in the output (`sort_keys=True`) so diffs are
deterministic and git history stays clean.

## Status mapping

| Category ID | Badge label | Passing suffix | Failing suffix |
|---|---|---|---|
| `hacs_structure` | HACS Structure | Passing | Issues |
| `manifest_metadata` | Manifest | Passing | Issues |
| `modern_ha_patterns` | Config Flow | Present | Missing |
| `diagnostics_repairs` | Diagnostics | Present | Missing |
| `docs_support` | Docs | Passing | Issues |
| `maintenance_signals` | Maintenance | Passing | Issues |
| `tests_ci` | Tests & CI | Passing | Issues |
| *(umbrella)* | HassCheck | Signals Available | *(always lightgrey)* |

`Partial` applies as a middle-ground suffix for all non-umbrella categories
when the aggregate is neither fully passing nor fully failing.

A category where every rule returned `not_applicable` emits no badge file.

Label and suffix values are defined in `src/hasscheck/badges/policy.py`
(`CATEGORY_LABELS`, `ALLOWED_SUFFIXES`).

## Color mapping

| Status | Color |
|---|---|
| Passing / Present | `brightgreen` |
| Partial | `yellow` |
| Issues / Missing | `red` |
| Signals Available (umbrella) | `lightgrey` |

## Manifest file

Alongside the per-category badge files, `hasscheck badge` writes a
`manifest.json` in the same output directory:

```json
{
  "artifacts": [
    "hacs_structure.json",
    "manifest_metadata.json",
    "..."
  ],
  "schema_version": "0.6.0"
}
```

`schema_version` is defined by `BADGE_MANIFEST_SCHEMA_VERSION` in
`src/hasscheck/badges/policy.py`. Bump it only when the manifest JSON structure
changes — not when badge colors or messages change.

## GitHub Pages recipe

### Step 1 — Add to workflow

```yaml
- uses: Daily-Nerd/hasscheck@v1
  with:
    emit-badges: 'true'
    badges-out-dir: 'badges'
```

This runs `hasscheck badge` and uploads a `hasscheck-badges` artifact
containing the JSON files from the `badges/` directory.

### Step 2 — Publish to GitHub Pages (example)

Download the artifact from the previous run and commit the badge files to your
repository so shields.io can read them via a raw GitHub URL:

```yaml
- name: Download badges artifact
  uses: actions/download-artifact@v4
  with:
    name: hasscheck-badges
    path: badges/

- name: Commit badges
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add badges/
    git diff --cached --quiet || git commit -m "chore: update hasscheck badges"
    git push
```

The exact approach depends on your GitHub Pages setup. Options include:

- Committing to `main` and serving from `main/badges/`
- Committing to a `gh-pages` branch
- Using a dedicated Pages deployment action

The only requirement for shields.io is that the JSON file is publicly
accessible via HTTPS.

### Step 3 — Embed in README

Replace `OWNER/REPO/main` with your actual repository path:

```markdown
![HACS Structure](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/hacs_structure.json)
![Config Flow](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/modern_ha_patterns.json)
![Diagnostics](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/diagnostics_repairs.json)
![Tests & CI](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/tests_ci.json)
![HassCheck](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/OWNER/REPO/main/badges/hasscheck.json)
```

Badge JSON files must be publicly accessible for shields.io to read them.

## Forbidden language

The following tokens are forbidden in any badge label or message
(`FORBIDDEN_LABEL_TOKENS` in `src/hasscheck/badges/policy.py`):

```
certified, safe, approved, hacs ready, community ready
```

These are enforced at runtime by `assert_label_is_clean()` (raises
`BadgePolicyError`) and by a property test in `tests/test_badges_policy.py`.
A violation is a release-blocker.

See ADR 0007 for the full policy rationale.
