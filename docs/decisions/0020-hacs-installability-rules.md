# ADR 0020 — HACS installability rules

**Status**: Accepted
**Issue**: #145
**Date**: 2026-05-03

## Context

hasscheck already validates that `custom_components/` exists (`hacs.custom_components.exists`)
and that `hacs.json` is valid JSON (`hacs.file.parseable`). Those two rules cover presence
only. They do not verify that a repository can actually be installed by HACS — correct schema
keys, single-integration layout, content-delivery strategy, and human-readable documentation.

Nine new rules are introduced under the `hacs.*` namespace to cover these installability
semantics. Three rules require GitHub API access and must return `NOT_APPLICABLE` in
static-check mode; six rules operate on the working-tree filesystem only.

---

## Decisions

### D1 — New module `rules/hacs.py` (separate from `hacs_structure.py`)

**Decision**: Create `src/hasscheck/rules/hacs.py` instead of extending `hacs_structure.py`.

**Rationale**: Keeps structural-presence rules (`hacs_structure.py`) separated from
installability-semantics rules (`hacs.py`). Lower blast radius; independent evolution.

**Rejected**: Extend `hacs_structure.py` — mixing concerns makes future splits harder.

---

### D2 — Reuse `category="hacs_structure"` for all 9 rules

**Decision**: All 9 rules carry `category="hacs_structure"`.

**Rationale**: Avoids touching `checker.py` and `CATEGORY_LABELS`. A rename to
`hacs_installability` is deferred — separate PR, separate ADR.

**Rejected**: New `hacs_installability` category — scope creep for this change.

---

### D3 — GH-API rules return `NOT_APPLICABLE` locally

**Decision**: `hacs.release_zip_valid`, `hacs.github_release_assets_valid`, and
`hacs.repository_topics_present` always return `RuleStatus.NOT_APPLICABLE` in static mode.

**Rationale**: Mirrors the `version.matches.release_tag` precedent. No new HTTP
dependencies; hub-side enrichment deferred to a follow-up.

**Rejected**: HTTP calls in static check — adds network dependency, breaks offline mode.

---

### D4 — `_read_hacs_json()` private helper returns `dict | None`

**Decision**: Private module-level helper; does not promote `hacs.json` to `ProjectContext`.

**Rationale**: No call-site outside `hacs.py` yet. Promoting to `ProjectContext` is a
separate ADR (context footprint increase). Helper is a standard pattern already used by
`manifest.py`.

**Rejected**: `ProjectContext.hacs_json` field — premature for a single-module consumer.

---

### D5 — v1 schema = known-keys allowlist (frozenset, 11 keys)

**Decision**: `_HACS_KNOWN_KEYS` is a `frozenset` of exactly 11 HACS v1 top-level keys:
`name`, `content_in_root`, `zip_release`, `filename`, `hide_default_branch`,
`homeassistant`, `hacs`, `render_readme`, `country`, `iot_class`, `domains`.

**Rationale**: Small, deterministic, matches HACS docs snapshot as of 2026. Unknown-key
rejection is preferable to silent acceptance — surface unknown keys so authors fix them.

**Rejected**: Full JSON Schema validation — over-engineered for a flat, 11-key object;
`iot_class`/`domains` exclusion — those are confirmed v1 keys.

---

### D6 — `RuleDefinition` fields: `title=`, `why=`, `check=`

**Decision**: Use `title=`, `why=`, `check=` as per the actual `base.py` dataclass.

**Rationale**: Matches the canonical field names in `RuleDefinition`. Any invocation
hints using `name=`, `description=`, or `check_fn=` are wrong.

---

### D7 — `version="0.15.6"` on all 9 `RuleDefinition` instances

**Decision**: All new rules carry `version="0.15.6"` — the hasscheck release that ships them.

**Rationale**: `version` tracks when a rule was introduced, not the HA minimum version.
Consistent with `introduced_at_version` semantics.

---

### D8 — ADR number 0020

**Decision**: ADR file is `docs/decisions/0020-hacs-installability-rules.md`.

**Rationale**: 0017 = import-smoke-harness, 0018 = advisory-model, 0019 = diff-PR-comments.
0020 is the next free number.
