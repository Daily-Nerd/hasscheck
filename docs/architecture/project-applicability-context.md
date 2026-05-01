# Project applicability context architecture (v0.3)

## Goal

Allow maintainers to declare project-level applicability facts once in
`hasscheck.yaml`, then let selected rules use those facts to return
`not_applicable` without requiring repetitive per-rule overrides.

## Non-goal

This is not source-code auto-detection. v0.3 consumes explicit user-declared
context only.

## Example

```yaml
schema_version: "0.3.0"

applicability:
  supports_diagnostics: false
  has_user_fixable_repairs: false
  uses_config_flow: true

rules:
  repo.license.exists:
    status: manual_review
    reason: License decision pending before public release.
```

## Data flow

```text
CLI/checker
  -> discover_config(root)
  -> detect_project(root, applicability=config.applicability)
  -> run rules with ProjectContext(applicability=...)
  -> collect config-driven applicability changes
  -> apply v0.2 per-rule overrides
  -> build ReportSummary(categories, applicability_applied, overrides_applied)
```

## Model additions

```python
class ProjectApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supports_diagnostics: bool | None = None
    has_user_fixable_repairs: bool | None = None
    uses_config_flow: bool | None = None

class HassCheckConfig(BaseModel):
    schema_version: Literal["0.2.0", "0.3.0"] = "0.3.0"
    project: ProjectConfig | None = None
    applicability: ProjectApplicability | None = None
    rules: dict[str, RuleOverride] = Field(default_factory=dict)

class ApplicabilityApplied(BaseModel):
    count: int = 0
    rule_ids: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
```

`ProjectContext` should gain:

```python
applicability: ProjectApplicability | None = None
```

Do not use module globals. Tests must be able to inject context/config without
writing files.

## Rule consumer contracts

### `diagnostics.file.exists`

| Condition | Result |
|---|---|
| no integration | native `not_applicable` |
| `diagnostics.py` exists | `pass` |
| missing + `supports_diagnostics is false` | `not_applicable`, source `config` |
| missing + flag absent/true | native `warn` |

### `repairs.file.exists`

| Condition | Result |
|---|---|
| no integration | native `not_applicable` |
| `repairs.py` exists | `pass` |
| missing + `has_user_fixable_repairs is false` | `not_applicable`, source `config` |
| missing + flag absent/true | native `warn` |

### `config_flow.file.exists`

| Condition | Result |
|---|---|
| no integration | native `not_applicable` |
| `config_flow.py` exists | `pass` |
| missing + `uses_config_flow is false` | `not_applicable`, source `config` |
| missing + flag absent/true | native `warn` |

### `config_flow.manifest_flag_consistent`

| Condition | Result |
|---|---|
| file + manifest flag agree | `pass` |
| file exists but manifest flag is not true | `fail` |
| manifest flag true but file missing | `fail` |
| no file and no flag + `uses_config_flow is false` | `not_applicable`, source `config` |
| no file and no flag + flag absent/true | native `not_applicable` |

The flag is allowed to explain intentional absence. It is not allowed to hide a
mismatch.

## Interaction with v0.2 per-rule overrides

Rule-level overrides still apply post-hoc after rule execution.

If a project flag produces config N/A, then a matching per-rule override is a
natural N/A/no-op case and should not increment `overrides_applied`. The finding
is already config-driven and is counted in `applicability_applied`.

If a rule returns `warn` and a per-rule override exists, v0.2 behavior applies.

## Terminal output

When `summary.applicability_applied.count > 0`, terminal output should display a
summary line such as:

```text
2 applicability decision(s) applied from hasscheck.yaml.
```

Findings changed by project applicability should be visually marked using the
existing `(config)` marker or equivalent because `applicability.source ==
"config"`.

## Test strategy

Start with failing tests for:

1. Config schema accepts `applicability:` with the three v0.3 flags.
2. Unknown applicability key fails due to `extra="forbid"`.
3. Existing v0.2 config with only `rules:` still parses.
4. Each consuming rule converts missing optional files to config N/A only when
   its flag is explicitly false.
5. Natural PASS wins over false flags.
6. Config-flow consistency mismatches still fail despite `uses_config_flow:
   false`.
7. `summary.applicability_applied` is present, sorted, and counts changed
   findings.
8. Per-rule overrides still work and remain separately disclosed.
