# ADR 0010 — Provenance block: `report.provenance`, `verified_by` convention, schema 0.4.0

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.13.x (#130)

## Context

The hosted hub (`hasscheck-web`) will display a public "OIDC-verified provenance"
badge in v1.0. Before launch, the report shape must distinguish between:

- A **self-claimed** provenance (set by the CLI from `GITHUB_*` env vars — anyone
  can fabricate these)
- A **verified** provenance (attested by `hasscheck-web` after validating the
  GitHub OIDC token presented at publish time)

Without this distinction, users cannot tell whether a published report's
provenance was independently verified or simply self-reported by the publisher.

Additionally, CI users want to correlate a report back to the exact run
(repository, SHA, ref, workflow, run ID, attempt) that produced it. This is
useful for debugging and auditing purposes, even without OIDC verification.

## Decision

1. **Schema 0.4.0** introduces an optional `report.provenance` block. The field
   defaults to `null`, so all pre-v0.4.0 reports remain valid (additive per
   ADR 0009).

2. **The `Provenance` model** carries the following fields, all optional
   (`T | None = None`):

   | Field | Type | Set by CLI | Source |
   |---|---|---|---|
   | `source` | `"github_actions" \| "local" \| None` | yes | `GITHUB_ACTIONS` env var |
   | `repository` | `str \| None` | yes | `GITHUB_REPOSITORY` |
   | `commit_sha` | `str \| None` | yes | `GITHUB_SHA` |
   | `ref` | `str \| None` | yes | `GITHUB_REF` |
   | `workflow` | `str \| None` | yes | `GITHUB_WORKFLOW` |
   | `run_id` | `str \| None` | yes | `GITHUB_RUN_ID` |
   | `run_attempt` | `int \| None` | yes | `GITHUB_RUN_ATTEMPT` (coerced) |
   | `actor` | `str \| None` | yes | `GITHUB_ACTOR` |
   | `published_at` | `str \| None` | yes | UTC ISO-8601, set at report-build time |
   | `verified_by` | `str \| None` | **NEVER** | hub-only writer |

3. **The CLI MUST NOT set `verified_by`**. It is the exclusive writer right of
   `hasscheck-web`, set only after validating the GitHub OIDC JWT presented at
   publish time. The CLI leaves this field `null` always.

   - `provenance` is the *claim* — any publisher can fill it in.
   - `verified_by` is the *attestation* — only the hub can set it, and only after
     OIDC validation succeeds.

4. **`detect_provenance()`** in `src/hasscheck/provenance.py` reads env vars:
   - If `GITHUB_ACTIONS == "true"` → `source="github_actions"`, best-effort
     population of all `GITHUB_*` fields; missing vars yield `None` (no error).
   - Otherwise → `source="local"`, all env-derived fields `None`,
     `published_at` set to current UTC time.
   - `GITHUB_RUN_ATTEMPT` is coerced via `int(value)`; `ValueError` yields `None`
     (forgiving boundary, strict model).

5. **JSON serialization** keeps all fields including `null`-valued ones
   (no `exclude_none=True`). A stable, predictable shape is preferred over a
   sparse representation. "Field present, value unknown" ≠ "field never existed".
   Aligns with ADR 0009 (additive versioning).

6. **`verified_by` type is `str | None`**, not `Literal["hasscheck-web-oidc"] | None`.
   Future hub versions may introduce new verifier identifiers (e.g.,
   `"hasscheck-web-oidc-v2"`); the CLI should not gate the hub's vocabulary.
   Trust boundary is enforced by *writer identity*, not by the type system.

## Consequences

- **SCHEMA_VERSION bump**: `0.3.0` → `0.4.0` in `src/hasscheck/models.py`.
- **`config.py` Literal** widened to `"0.2.0" | "0.3.0" | "0.4.0"`. Default
  changed to `"0.4.0"`.
- **Lockstep release gate**: `hasscheck-web` MUST accept schema `0.4.0`
  (with optional `provenance`) BEFORE the OSS v0.13.x tag ships. Shipping OSS
  first risks rejecting publishes from early upgraders.
- **Branch-name leakage via `ref`**: already public in GitHub Actions logs;
  `hasscheck.yaml`-based publish is opt-in. Accepted risk.
- **Future CI providers** (GitLab CI, CircleCI, etc.) will be added in future
  minor schema bumps (additive per ADR 0009). `source` stays
  `"github_actions" | "local" | None` in v0.4.0.
- Non-GH-Actions runs always produce `source="local"` with `published_at` set.

## Related

- ADR 0008 — Hosted reports publish contract (transport + auth)
- ADR 0009 — Schema versioning policy (additive bump rule)
- Issue #130 — Provenance block implementation
- Issue #131 — `publish --dry-run` (references this ADR)
- Issue #132 — Upgrade Radar (references this ADR)
