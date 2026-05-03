# ADR 0019 — Diff-aware PR comments

**Status**: Accepted
**Issue**: #150
**Date**: 2026-05-02

## Context

hasscheck currently posts a full-state PR comment via `comment-pr: 'true'`.
As rulesets grow, that comment becomes noisy for reviewers who only care about
regressions. A diff-aware mode should show only new / fixed findings between
the base branch and the PR HEAD.

---

## Decisions

### D1 — `ReportDelta` as a frozen dataclass with tuple fields

**Decision**: `@dataclass(frozen=True)` in `diff.py`, fields are `tuple[Finding, ...]`.

**Rationale**: It is a computation result, not a versioned schema. No
serialization/validation needed at the type. Tuples make the dataclass hashable
and immutable, matching baseline conventions (`BaselineEntry` is Pydantic because
it persists; `FindingPartition` in `baseline/core.py` is a frozen dataclass
because it doesn't).

**Rejected alternatives**: Pydantic `BaseModel` — over-engineered for a transient
struct; plain `NamedTuple` — less explicit, can't add validators later.

**Reversal cost**: Low.

---

### D2 — Reuse `compute_finding_hash` from `hasscheck.baseline` (no extraction)

**Decision**: `from hasscheck.baseline import compute_finding_hash`. No move to
`hasscheck.hashing`.

**Rationale**: ADR 0016 owns hash-policy semantics (`rule_id | path |
normalized_message`). Forking or moving the function risks divergence.

**Rejected alternatives**: Extract to `hasscheck.hashing` (medium-effort refactor
for zero functional gain; breaks ADR 0016 ownership); duplicate the function
(ADR 0016 violation, drift risk).

**Reversal cost**: Low.

---

### D3 — Markdown comment carries sticky marker `<!-- hasscheck-pr-comment -->`

**Decision**: Marker comment as the first line of `delta_to_md` output.

**Rationale**: Current action uses `gh pr comment --edit-last`, which is positional.
A marker gives forward-compat for explicit content-based detection without forcing
a refactor today.

**Rejected alternatives**: No marker (lock-in to `--edit-last`; no upgrade path);
separate state file (more moving parts).

**Reversal cost**: Low (cosmetic).

---

### D4 — `diff` is a root Typer command (not a sub-app)

**Decision**: `@app.command("diff")` directly on `app` in `cli.py`.

**Rationale**: `diff` has a single verb taking two file arguments — sub-app would
add ceremony with no commands to host.

**Rejected alternatives**: `hasscheck diff <subcmd>` sub-app (no second verb in
scope); standalone script (loses Typer help, version flag, error handling).

**Reversal cost**: Low.

---

### D5 — `diff-mode` is a new orthogonal action input (not a behavior change to `comment-pr`)

**Decision**: New `diff-mode: 'false'` input. Existing `comment-pr` semantics
unchanged.

**Rationale**: Backward compatibility — existing users who set `comment-pr: 'true'`
continue to see the full-state report. Opt-in keeps the dual-checkout cost opt-in.

**Rejected alternatives**: Repurpose `comment-pr` to always diff (breaking change);
make `diff-mode` imply `comment-pr` (couples two decisions).

**Reversal cost**: Medium (would need a deprecation cycle if reversed).

---

### D6 — Module location: flat `src/hasscheck/diff.py`

**Decision**: Single file `diff.py`, not a `diff/` package.

**Rationale**: ~3 public symbols, ~120 LOC expected. Diff is small enough to stay
flat; can be promoted later if needed.

**Rejected alternatives**: `src/hasscheck/diff/{core.py,cli.py}` package
(premature); add to `output.py` (semantic mismatch).

**Reversal cost**: Low (pure refactor).

---

### D7 — Exit codes: `0`/`1`/`2` semantic split

**Decision**: `0` = no new findings, `1` = new findings exist, `2` = I/O or parse
error.

**Rationale**: Mirrors POSIX convention where `1` is "found something" and `2` is
"tool failure". Lets CI gate on "PR introduced new findings" without conflating with
parse errors.

**Rejected alternatives**: Always `0` (loses CI gate signal); `0` vs. `1` only
(parse errors masquerade as findings); use `--strict` flag (extra surface).

**Reversal cost**: Medium (callers may script on exit codes).

---

### D8 — `ReportDelta` is NOT re-exported from `hasscheck/__init__.py`

**Decision**: No change to `hasscheck/__init__.py`. `diff` module accessed only via
`from hasscheck.diff import ...`.

**Rationale**: Internal computation surface, not a public Python API. Re-exporting
commits to backward compat we don't owe yet.

**Rejected alternatives**: Re-export at root (premature commitment); export under
`hasscheck.api` (no such namespace exists yet).

**Reversal cost**: Low (additive change later).

---

## v1 Limitations

- Status changes (FAIL → WARN on same rule_id/path/message) are NOT regressions —
  hash does not include status field (intentional per ADR 0016 policy).
- No `allow_regression` gate config.
- No per-line PR annotations.
- No caching of base-branch JSON across runs.

## Parent-workflow contract

When `diff-mode: 'true'`, the parent workflow MUST configure:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

Without `fetch-depth: 0`, shallow clones will fail to find the base SHA.
