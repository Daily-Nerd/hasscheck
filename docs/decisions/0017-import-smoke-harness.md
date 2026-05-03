# ADR-0017: Import Smoke Harness

## Status

Accepted

## Context

Static analysis checks in `hasscheck` inspect manifest metadata, code structure, and CI configuration, but they cannot detect runtime breakage caused by incompatible Home Assistant API changes between HA versions. An integration may pass all static checks yet fail at import time when loaded against a newer (or older) HA release due to removed attributes, renamed modules, or altered base classes.

Issue #143 introduces a venv-based import-probing harness (`hasscheck smoke`) to close this gap. The harness:

1. Creates an isolated Python virtual environment (via `uv venv`) pinned to a specific HA version.
2. Installs `homeassistant==<version>` plus integration requirements.
3. Runs `python -c "import <module>"` for each module in the integration.
4. Maps the subprocess exit code and stderr to `Finding` objects using the existing `HassCheckReport` model (Approach C).

See proposal `sdd/143-smoke-harness/proposal` for full context.

## Decision

- **Isolation via `uv venv`** — one virtualenv per (ha_version, python_version) tuple, keyed under a user cache directory. No container dependency.
- **Approach C — reuse `HassCheckReport`** — the smoke result is a `HassCheckReport` with `target.check_mode="import-smoke"` and findings in `category="compatibility"`. The existing terminal renderer, JSON serialiser, and publish path all work without modification.
- **Single subprocess boundary in `runner.py`** — all `subprocess.run` calls are isolated in one module (`hasscheck.smoke.runner`), which makes monkeypatching in tests trivial (one symbol).
- **Stdlib for cache-dir resolution** — no `platformdirs` dependency; uses `$XDG_CACHE_HOME` / `~/.cache` on Linux/macOS and `%LOCALAPPDATA%` on Windows.
- **`RunSmokeResult` as a frozen dataclass** — the internal orchestration container is NOT a Pydantic model; the serialised artifact is `HassCheckReport`.
- **Smoke findings are non-overridable structurally** — smoke rules (`smoke.import.fail`, `smoke.import.error`, `smoke.harness.error`) are NOT registered in the `RULES` registry, so `apply_overrides()` can never suppress them.

## Considered Alternatives

### AD-01: Container isolation (Docker / Podman)

**Rejected.** Requires a container runtime as an additional dependency. CI cold-start is significantly slower (container pull vs. uv venv creation). Adds complexity without proportional value for v1. Deferred to v2 if deeper isolation is required.

### AD-02: Standalone `SmokeReport` Pydantic model (Approach A)

**Rejected.** Forks the publish path and terminal renderer. Two divergent report models increase maintenance surface. Approach C achieves the same user-visible result without a schema bump.

### AD-03: Schema bump to 0.6.0 with `smoke_findings` field (Approach B)

**Rejected.** No consumer is ready to handle a new top-level field. Premature schema evolution; deferred until the hub explicitly requests it.

### AD-04: Raw Rich output bypassing `Finding` (Approach D)

**Rejected.** Violates the project discipline of expressing all check results as `Finding` objects. Breaks structured output (`--json`), the terminal renderer, and future baseline diffing.

## Consequences

- `runner.py` is the **sole subprocess boundary** — tests monkeypatch one symbol (`hasscheck.smoke.runner.subprocess.run`).
- Cache lives under `~/.cache/hasscheck/smoke/<key>` (Linux/macOS). First run is slow (~100 MB HA wheel download); subsequent runs reuse the cached venv.
- Default timeout is 120 seconds per HA version; overridable via `--timeout`.
- `category="compatibility"` is registered in `CATEGORY_LABELS` in `checker.py` but is never produced by the static `run_check()` path (no rule in `RULES` carries that category).
- Exit codes follow the `hasscheck smoke` contract: `0` = all pass, `1` = at least one FAIL finding, `2` = harness error or bad CLI args.
- Multi-version output (`--ha-version-matrix`) is sequential in v1; concurrency deferred to v2.

## References

- Issue: #143
- Proposal: `sdd/143-smoke-harness/proposal`
- Spec: `sdd/143-smoke-harness/spec`
- Design: `sdd/143-smoke-harness/design`
