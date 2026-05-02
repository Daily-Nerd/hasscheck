# ADR 0013 — Integration version identity + ReportTarget + ReportValidity (schema 0.5.0)

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v0.14.x (#141)

## Context

HassCheck schema 0.4.0 (ADR 0009) captures the environment of a check run via
the `provenance` block — CI context, commit SHA, repository — but carries no
identity for the integration itself. A report today cannot answer: "Which
version of this integration was checked?" or "Is this report still current?".
That gap makes it impossible to build the hub's compatibility matrix, which
requires pairing an integration version with a HA version and a check result.

ADR 0012 locked the wording contract: HassCheck reports are exact-build
signals, not general compatibility claims. To surface even the first version-
tagged verdict, the hub needs the integration version, its source (how we
detected it), and a validity window so stale reports can be identified without
re-running the check. Currently, that data is not emitted.

The integration version may come from several sources — the canonical
`manifest.json["version"]` field, a git annotated tag when the manifest carries
no version, a GitHub Actions `GITHUB_REF` pointing to a release tag, or HACS
metadata in environments where HACS is installed. These sources have a natural
priority order and must be collapsed into a single `(integration_version,
integration_version_source)` pair with a frozen, deterministic tie-breaking
rule.

ADR 0012 §7 mandated a CLI footer referencing the compatibility claim policy
whenever a report carries a populated `report.target.ha_version`. That
requirement cannot be satisfied until a `target` block exists in the schema.
This ADR delivers the block and wires the footer simultaneously so the
obligation never splits across two PRs.

The hub's publish endpoint (ADR 0008) uses strict schema-version matching: an
HTTP 422 is returned for any payload whose `schema_version` does not match
the server's expected version. Shipping this schema bump requires hub-side
acceptance to land before the OSS tag — the same three-step lockstep used for
schema 0.4.0.

## Decision

1. **MINOR bump 0.4.0 → 0.5.0** per the additive-only policy in ADR 0009. No
   existing field becomes required; new fields default to `None` or a safe
   literal so that all 0.4.0 consumers continue to parse 0.5.0 payloads without
   changes.

2. **`ProjectInfo` gains four optional fields**: `integration_version`,
   `integration_version_source` (Literal, default `"unknown"`),
   `manifest_hash`, and `requirements_hash`. These duplicate the identity
   information at the project level for consumers that do not process the
   `target` envelope.

3. **New `ReportTarget` model** — 8 fields, all optional — identifies the exact
   build: `integration_domain`, `integration_version`,
   `integration_version_source`, `integration_release_tag`, `commit_sha`,
   `ha_version`, `python_version`, and `check_mode`. All default to `None` or a
   safe literal. Added to `HassCheckReport` as `target: ReportTarget | None = None`.

4. **New `ReportValidity` model** — 4 fields — describes the freshness
   contract: `claim_scope` (frozen as `"exact_build_only"`), `checked_at`
   (ISO-8601 UTC with Z suffix), `expires_after_days` (default 90), and
   `superseded_by_integration_version`. Added to `HassCheckReport` as
   `validity: ReportValidity | None = None`.

5. **Hub-only writer contract for `superseded_by_integration_version`**: the
   CLI always writes `None`. The hub sets this field after indexing, using the
   same trust boundary as `Provenance.verified_by`. Enforced by a pytest
   contract test (`test_cli_never_sets_superseded_by_integration_version`)
   rather than a Pydantic validator, so hub round-trips are not broken.

6. **Detection priority frozen**: `manifest.json["version"]` → `git_tag` (via
   `git describe --tags --exact-match HEAD`, D6 exact invocation) →
   `github_release` (GITHUB_REF env matches `refs/tags/*`) → `hacs_metadata`
   (deferred stub, always returns None in this PR) → `unknown`. First match wins
   for `integration_version` and `integration_version_source`. Other fields
   (`commit_sha`, `python_version`, `integration_domain`) populate
   independently from their own sources.

7. **CLI footer wired in text and markdown output**, gated on
   `report.target and report.target.ha_version`, per ADR 0012 §7. Footer text
   is frozen: "Compatibility claims policy:
   https://github.com/Daily-Nerd/hasscheck/blob/main/docs/compatibility-claim-policy.md
   — HassCheck reports are exact-build signals." JSON output is unchanged. The
   footer is dormant in this PR because `ha_version` is always `None` from
   `detect_target()` until the smoke harness (#150) lands.

8. **Lockstep gate with hasscheck-web**: the OSS tag is blocked until the hub
   deploys 0.5.0 acceptance and a smoke test passes. See Consequences.

## Consequences

### Hub-side dependency (3-step lockstep)

1. **hasscheck-web** deploys schema 0.5.0 acceptance — `target` and `validity`
   are optional in the payload validator; the endpoint returns 200 for 0.5.0
   payloads with or without those fields. This is a separate hub PR deployed
   first.
2. **Hub smoke test** confirms a 0.5.0 publish succeeds: a manual or scripted
   `hasscheck publish` from the feature branch hits the production hub and
   returns 200, not 422.
3. **OSS v0.14.x tagged + released**. Step 3 is BLOCKED until step 2 returns
   green.

### Deferred items

- **HACS metadata detection**: `_hacs_metadata_version()` is a stub that always
  returns `None`. The "hacs_metadata" Literal value is reserved but never
  emitted in this PR. Detection is deferred because HACS metadata is only
  accessible in environments with an HA install fixture, making it untestable
  in CI. See ADR 0013 §Consequences.
- **`expires_after_days` configuration support**: hardcoded to 90. Plumbing
  into `hasscheck.yaml` is a follow-up.
- **PEP 508 normalization for `requirements_hash`**: the hash uses lexicographic
  sort of raw PEP 508 strings only. Normalization (canonicalization of package
  names and extras) is deferred per the proposal risk analysis.
- **Per-rule min/max HA version backfill**: a separate PR (#147 follow-up).
- **`is_current` field**: not in this PR. The hub can derive freshness from
  `checked_at + expires_after_days`. This field is a potential schema 0.6.0
  addition if hub freshness logic requires it.
- **`ha_version` population**: always `None` in this PR. The footer code ships
  dormant and lights up automatically when the smoke harness (#150) populates
  `ha_version`.

### ADR 0012 wording inheritance

This ADR delivers the CLI footer required by ADR 0012 §7. The footer wording
is frozen in this ADR. Any modification to the footer text requires an ADR
amendment.

## Alternatives considered

- **Commit-SHA-only identity**: a `commit_sha`-only signal is insufficient for
  human-readable compatibility queries. Users need to correlate a check result
  with an integration version that appears on GitHub Releases and in HACS —
  not with a 40-character hash.
- **Flat schema (no `ReportTarget` envelope)**: placing identity fields
  directly on `ProjectInfo` couples version identity to project structure,
  makes hub deduplication harder, and pollutes the top-level report namespace.
  An envelope is cleaner and mirrors `provenance` precedent.
- **Opt-in `--with-target` CLI flag**: the hub needs identity on every report
  it indexes; an opt-in flag defeats the always-on requirement and makes the
  footer inconsistent.
- **Defer footer to #150**: splitting the ADR 0012 §7 obligation across two PRs
  risks wording drift. Shipping the footer code in this PR — dormant but
  correct — is lower risk and avoids a second ADR.

## Related

- ADR 0008 — Hub lockstep (strict schema-version matching on publish)
- ADR 0009 — Schema versioning policy (additive bump rule, backwards
  compatibility guarantee)
- ADR 0010 — Provenance block (`verified_by` trust boundary; pattern mirrored
  by `superseded_by_integration_version`)
- ADR 0012 — Compatibility claim policy (exact-build wording; §7 mandates the
  footer wired in this ADR)
- Issue #141 — This ADR's source issue
- Issue #147 — Rule definition metadata (parallel schema work)
- Issue #150 — Smoke harness (populates `ha_version`; footer lights up when
  this lands)
- Issue #154 — ADR 0012 source issue
- Issue #155 — Related schema work
- hasscheck-web companion issue — Hub 0.5.0 acceptance (step 1 of lockstep)
