# Scaffolding architecture (v0.4)

## Goal

Provide a `hasscheck scaffold` CLI subapp that generates conservative starter
files for common Home Assistant integration patterns (diagnostics, repairs,
GitHub Action workflow). The infrastructure is introduced in v0.4.0; concrete
subcommands follow in subsequent tasks.

## Five architecture decisions

### A — Static templates + string.Template

Template files live at `src/hasscheck/scaffold/templates/*.tmpl` and are
loaded at runtime via `importlib.resources.files("hasscheck.scaffold.templates")`.
Substitution uses stdlib `string.Template` with `$variable` placeholders.

This keeps hasscheck dependency-free (no Jinja2) and enforces template
simplicity — templates cannot contain logic, only substitution.

### B — Module layout

```
src/hasscheck/scaffold/
    __init__.py        # public API re-exports
    cli.py             # Typer subapp (scaffold_app)
    engine.py          # load_template, render, write_or_refuse, check_applicability_gate
    templates/         # .tmpl files (empty in v0.4.0 infra task)
        .gitkeep
```

The `scaffold_app` Typer subapp is registered in `src/hasscheck/cli.py` via:

```python
app.add_typer(scaffold_app, name="scaffold")
```

### C — Applicability gate

`engine.check_applicability_gate(config, scaffold_type)` consults the
`HassCheckConfig.applicability` block from `hasscheck.yaml` and returns:

- A human-readable **warning string** → refuse generation (caller decides how to present it)
- `None` → generation is allowed

Refuse only when the relevant flag is **explicitly `False`**. Absent config,
absent block, `None`, and `True` all allow generation. This mirrors v0.3's
"flags only soften" contract.

| scaffold_type   | applicability flag          |
|-----------------|-----------------------------|
| `"diagnostics"` | `supports_diagnostics`      |
| `"repairs"`     | `has_user_fixable_repairs`  |
| `"github-action"` | _(no gate)_               |

### D — write_or_refuse safe-write helper

`engine.write_or_refuse(path, content, *, force=False, dry_run=False)`:

| condition                          | behaviour                                   |
|------------------------------------|---------------------------------------------|
| file does not exist                | write and return                            |
| file exists, force=False           | raise `FileExistsError` with helpful message |
| file exists, force=True            | overwrite and return                        |
| dry_run=True (any existence state) | print to stdout, do NOT write               |

All scaffold subcommands delegate file writing to this helper. They expose
`--force` and `--dry-run` CLI flags that map directly to the `force` and
`dry_run` kwargs.

### E — engine.py does NOT touch rules

The `command` field on `FixSuggestion` (added in a future task) and all
rule definitions remain outside `engine.py`. The scaffold engine is a pure
file-generation utility; it has no knowledge of the rules system.

## Data flow

```
hasscheck scaffold <subcommand> [options]
         |
         v
  check_applicability_gate(config, scaffold_type)
         |                          |
    returns warning           returns None
         |                          |
    typer.echo + Exit        load_template(name)
                                     |
                              render(template, vars)
                                     |
                           write_or_refuse(path, content,
                                           force=..., dry_run=...)
```

## Resource loading

`importlib.resources.files()` (Python 3.9+, project requires 3.12+) is used
to locate templates bundled inside the installed package. This works correctly
from the source tree, an editable install, and a built wheel — no `__file__`
path manipulation required.

Hatchling (the build backend) includes all files under `src/` by default; no
explicit `include` rule is needed for the templates directory.

## Testing strategy

`tests/test_scaffold_engine.py` covers all four engine functions:

- `load_template`: patched via `unittest.mock.patch` — no actual .tmpl files
  needed in the infra task.
- `render`: direct string assertions.
- `write_or_refuse`: uses `tmp_path` fixture; tests all four branches (new
  file, exists+refuse, exists+force, dry_run).
- `check_applicability_gate`: covers None config, each flag state (False/True/None),
  and the absence of a gate for `github-action`.
