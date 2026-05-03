# ADR 0016 — Baseline mode: file-based suppression of pre-existing findings

- **Status**: Accepted
- **Date**: 2026-05-02
- **Tag**: v0.16.x (#149)

## Context

Adopting hasscheck on a brownfield repository (one with existing technical debt)
produces a large number of FAIL/WARN findings on the first run. This makes it
hard to gate CI on only *new* regressions while allowing the team to address
existing issues incrementally. Whole-rule suppression (`rules: status: not_applicable`)
destroys signal permanently and couples suppression to rule IDs rather than
specific findings. A time-bounded "accept this known debt" mechanism is needed
that preserves regression detection while surfacing resolved debt as wins.

## Decision

### 1. `baseline update` MERGES, never replaces (D1)

When `hasscheck baseline update` is run on an existing baseline file:
- Entries whose `finding_hash` still matches a live FAIL/WARN finding **preserve** their `reason` and `accepted_at` fields.
- Entries whose `finding_hash` no longer matches any live finding are **dropped** (the debt was resolved).
- Live FAIL/WARN findings with no matching baseline entry are **added** with `reason=""` and today's `accepted_at`.

Header fields (`generated_at`, `hasscheck_version`, `ruleset`) are always refreshed.

### 2. `baseline drop` removes by `--rule`; `--path` narrows (D2)

`hasscheck baseline drop --rule <id>` removes ALL entries matching `rule_id=<id>`.
`hasscheck baseline drop --rule <id> --path <file_path>` removes only the specific `(rule_id, path)` entry.
If no entries match, the command exits non-zero with an error (typo guard). There is no `--dry-run` or `--all` in v1.

### 3. JSON output stays clean (D3)

The `--baseline` flag is a CLI-layer concern only. The `HassCheckReport` JSON contract is not modified. `report_to_json` is not touched. No `baseline_status` fields are added to `Finding`. Schema version is not bumped by this feature.

### 4. `[accepted]`/`[new]`/`[fixed]` labels are terminal-only (D4)

Terminal output (`--format terminal`) shows per-finding labels and a "N fixed since baseline" summary line when `--baseline` is passed. Markdown output (`--format md`) and JSON output are not modified. This avoids coupling the report contract to baseline state.

### 5. `baseline create` refuses to overwrite; `--force` overrides (D5)

`hasscheck baseline create` exits non-zero if `hasscheck-baseline.yaml` already exists at the target path, and the error message points the user to `baseline update` as the safe incremental workflow. Passing `--force` bypasses this guard and overwrites the file. This prevents accidental loss of `reason` annotations accumulated over time.

### 6. Only FAIL and WARN findings enter the baseline (D6)

`NOT_APPLICABLE`, `MANUAL_REVIEW`, and `PASS` findings are not eligible for the baseline. These statuses are not regressions and including them would inflate the baseline file with no actionable signal. The `_BASELINE_ELIGIBLE = frozenset({RuleStatus.FAIL, RuleStatus.WARN})` constant governs eligibility throughout the data layer.

### 7. CLI-layer `FindingPartition`; no `Finding` mutation (architecture)

The partition is computed in the CLI `check` command via `partition_findings(report.findings, baseline_file)` and passed to `print_terminal_report` as an optional keyword argument. The `Finding` model is not modified. Gate decisions consume `partition.new` instead of `report.findings` when a baseline is active. This is "Approach C" from the exploration: no schema bump, no public-contract leak, and gate/profile/gate-modes compose via `list[Finding]`.

### 8. Hash policy: `sha256(rule_id|path|normalized_message)[:8]` (architecture)

The finding hash is computed as:
```
sha256(f"{rule_id}|{path or ''}|{normalized_message}".encode("utf-8")).hexdigest()[:8]
```
where `normalized_message = " ".join(message.lower().split())`.

Fields **excluded** from the hash: `status`, `severity`, `rule_version`, `source.checked_at`.

8 hex characters = 32-bit collision space, ample for HA-integration baselines where the number of distinct findings is typically under 100. The normalization absorbs whitespace and casing rewrites; intentional message changes in rule code MAY require running `baseline update` — this is documented behavior, not a limitation.

### 9. `baseline/` is a package, not a module (architecture)

The data layer (`BaselineEntry`, `BaselineFile`, `FindingPartition`, hashing, partition, YAML I/O, builder helpers) lives in `src/hasscheck/baseline/core.py`. The CLI subapp lives in `src/hasscheck/baseline/cli.py`. The public surface is re-exported from `src/hasscheck/baseline/__init__.py`. Python disallows a same-named module and package on the import path, so `baseline.py` was never an option once the subapp was split out.

### 10. No `HassCheckConfig` schema bump (architecture)

The `--baseline` flag is a pure CLI option. It is not persisted in `hasscheck.yaml`. The `HassCheckConfig` Pydantic model is unchanged. Rollback is `git revert` of this feature branch; no migration path is needed.

## Interactions

### Profile suppression

When a profile (ADR 0015) or per-rule override sets a finding's status to `NOT_APPLICABLE`, that finding exits the `_BASELINE_ELIGIBLE` set and cannot match a baseline entry. If a previously baselined rule is later suppressed by a profile change, its baseline entry will appear as `[fixed]` in terminal output on the next run — a cosmetic artifact, not a real fix. This is conservative behavior: the entry can be cleaned up with `baseline drop --rule <id>`.

### Gate modes (ADR 0014)

Gate modes compose cleanly. `should_exit_nonzero(gate_findings, gate)` receives `partition.new` instead of `report.findings` when a baseline is active. This means gate mode evaluation (advisory, strict-required, hacs-publish, upgrade-radar) applies only to genuinely new findings, not baselined ones.

## Consequences

- The feature is entirely additive. Without `--baseline`, behavior is identical to pre-0.16 hasscheck.
- `hasscheck baseline` is a new top-level subapp discoverable via `hasscheck baseline --help`.
- The `hasscheck-baseline.yaml` file should be committed to version control alongside `hasscheck.yaml`.
- Hash brittleness on rule message rewrites is an accepted cost; `baseline update` is the recovery path.
- The `accepted_at` date and `reason` fields enable future tooling (age-based reminders, audit reports) without schema changes.

## Alternatives considered

- **Add `baseline_status` to `Finding` model** — rejected per Decision 7; pollutes the public JSON contract and requires a schema version bump.
- **Auto-discover `hasscheck-baseline.yaml`** — rejected; explicit beats implicit. The file may live in a non-root location in monorepos.
- **Auto-regenerate baseline on every check** — rejected; silent debt growth defeats the purpose.
- **`baseline drop --all`** — deferred; destructive shortcut. Want explicit per-rule UX first to understand usage patterns.
- **`ruamel.yaml` for comment preservation** — deferred; PyYAML is sufficient for v1. `ruamel.yaml` adds a dependency and complexity.
- **`schema_version` field on `BaselineFile`** — deferred; the format is trivial and a version field can be added without breaking existing files when needed.
- **Store baseline entries in `hasscheck.yaml`** — rejected; separates concerns and avoids inflating the config file used by the gate.

## Related

- ADR 0014 — Quality gate modes (#148)
- ADR 0015 — Quality profiles (#146)
- Issue #149 — Source issue
- Proposal: `sdd/149-baseline-mode/proposal` (engram)
