# ADR 0005 — Scaffolding policy for v0.4

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.4 scope

## Context

v0.3 ships project applicability flags. Once maintainers declare what their
integration supports (or does not), a natural next step is generating conservative
starter files for those patterns — diagnostics, repairs, a GitHub Action workflow.

This ADR records the three locked decisions that govern how scaffold generation
works across all scaffold subcommands introduced in v0.4.

## Decisions

### (a) Static templates + string.Template

Templates are static `.tmpl` files stored in
`src/hasscheck/scaffold/templates/`. They use stdlib `string.Template`
(`$variable` syntax) for substitution.

**No Jinja2, no new runtime dependencies.**

Reasoning: the substitution needs are minimal (domain name, a handful of strings).
Jinja2 would add a dependency, increase install size, and introduce control-flow
features that encourage overly complex templates. `string.Template` enforces
simplicity at the language level.

Reversal cost: **medium** — switching to Jinja2 later requires updating all
templates and the render() call site, but is straightforward.

### (b) Applicability gate: refuse if flag is explicitly false

`engine.check_applicability_gate(config, scaffold_type)` returns a warning
string (refuse) if the relevant applicability flag in `hasscheck.yaml` is
**explicitly `False`**. It returns `None` (allow) in all other cases:

- No config file
- Config file with no `applicability:` block
- Flag set to `None` (unset)
- Flag set to `True`

Mapping:
- `"diagnostics"` scaffold type → `supports_diagnostics`
- `"repairs"` scaffold type → `has_user_fixable_repairs`
- `"github-action"` → no gate (always allowed)

Reasoning: the gate exists to prevent generating files that the maintainer has
explicitly declared irrelevant. An absent or `None` flag means "unknown" — we
should not block generation on ambiguity.

### (c) Refuse-by-default if file exists

`engine.write_or_refuse(path, content, *, force=False, dry_run=False)` raises
`FileExistsError` with a helpful message if the destination file already exists
and `force=False`.

- `force=True`: overwrite silently.
- `dry_run=True`: print content to stdout, write nothing, skip the existence check.

Reasoning: scaffolded files are starter files. Overwriting an existing
implementation without consent would destroy work. The default is the safe option;
opt-in `--force` is available for re-scaffolding.

## Scope

### In (v0.4.0 infrastructure task)

- `hasscheck scaffold` Typer subapp, wired into main app.
- `engine.py`: `load_template()`, `render()`, `write_or_refuse()`,
  `check_applicability_gate()`.
- Template directory scaffold (`src/hasscheck/scaffold/templates/`).
- Concrete scaffold subcommands added in subsequent tasks.

### Out

- Non-standard template engines.
- Multi-file scaffold bundles in a single invocation.
- Remote template sources.
- Scaffold undo / rollback.

## Alternatives rejected

### Jinja2

Rejected. Over-engineered for the current use case. Adds a dependency and
invites template complexity. Can be introduced later if substitution needs grow.

### Prompt on file exists (instead of raise)

Rejected. CLI tools should be scriptable. Interactive prompts break non-TTY
usage (CI, pipes). `--force` and `--dry-run` flags give users full control
without requiring stdin interaction.

### Gate on flag absent (treat absent as false)

Rejected. Absent means "I haven't declared anything yet." Refusing generation
for an undeclared flag would break the out-of-the-box experience and contradict
v0.3's explicit-declaration-only model.
