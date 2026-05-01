# Contributing to HassCheck

Thanks for considering a contribution. HassCheck is a small, focused tool — a few patterns keep it that way.

## Before you start

- **File an issue first.** Every change goes through maintainer review BEFORE implementation. The issue is where scope, severity, and rule semantics get pinned down. PRs without an approved issue may be closed.
- **Read the closest existing rule.** Pattern-match instead of inventing. Rules follow a uniform shape (`RuleDefinition` + check function + `RULES` list).
- **Read the relevant ADR.** Rules: `docs/decisions/0006-ruleset-versioning.md`. Schema: `docs/decisions/0009-schema-versioning.md`. Publish contract: `docs/decisions/0008-hosted-reports-publish-contract.md`.

## Setting up

```bash
git clone https://github.com/Daily-Nerd/hasscheck.git
cd hasscheck
uv sync
uv run pytest
```

Requires Python 3.12+. Tests must pass before any commit (pre-commit hook enforces the version-consistency check; please run `uv run pytest` yourself before pushing).

## Adding a rule

1. **Get the issue approved** — `status:approved` label, rule semantics confirmed.
2. **Pick the right module** in `src/hasscheck/rules/`. New category → new module + add to `registry.py`.
3. **Write the test first** (`tests/test_rules_<module>.py`). RED → GREEN. Cover PASS, FAIL/WARN, NOT_APPLICABLE, and parse-error scenarios where applicable.
4. **Implement the rule.** `RuleDefinition(id, version="1.0.0", category, severity, ...)`.
5. **Update the rule audit** (`tests/test_rules_meta.py`) — total count + the appropriate set (overridable / locked).
6. **Update README** "Current rule set" table.
7. **Add a `docs/rules/<rule_id>.md` page** matching the template of existing pages.

## Rule philosophy

- **Sourced**: every finding cites an HA dev docs URL with a `source_checked_at` date.
- **Conservative**: AST and heuristic rules WARN, never FAIL. False positives are worse than false negatives for a maintainer-facing tool.
- **Overridable by default** unless the rule is a correctness check (identity, validity).
- **No certification language.** Forbidden tokens: `certify`, `approved`, `safe`, `ready`, `quality tier`. A property test enforces this at runtime.

## Commits

- Conventional commits required: `feat(rules): ...`, `fix(cli): ...`, `docs(readme): ...`, `chore(release): ...`.
- No AI attribution / `Co-Authored-By` trailers.
- One concern per commit. Squash-merge by default; keep history readable on the main branch.

## What we won't accept

- Rules that fail repos for stylistic preferences (formatting, line length).
- Rules that require running tests, linters, or builds in the user's project — HassCheck is static analysis only.
- Server-side dependencies in OSS rules (the hosted service is opt-in; OSS works offline).
- "Quality tier" or certification framings of any kind.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## Questions

Open a `question`-labeled issue. We don't have a Discussions tab yet; issues are the channel.
