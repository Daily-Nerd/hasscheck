# HassCheck demo

> **Visual demo**: see [`docs/demo.gif`](demo.gif) when rendered. The GIF is generated from
> [`docs/demo.sh`](demo.sh) — see [`docs/recording.md`](recording.md) to regenerate.

Run HassCheck against the tracked `bad_integration` fixture, see findings, run a scaffold, see improvement.

## 1. Check the bad fixture

```bash
uv run hasscheck check --path examples/bad_integration
```

Expected output (abridged):

```text
HassCheck Summary

Diagnostics/Repairs: 1 / 3
Docs/Support: 1 / 6
HACS Structure: 1 / 3
Manifest Metadata: 8 / 11
Modern HA Patterns: 2 / 3
Tests/CI: 0 / 2

Overall: Informational only
Security Review: Not performed
Official HA Tier: Not assigned
HACS Acceptance: Not guaranteed

...
| FAIL | manifest.domain.matches_directory | manifest.json domain "wrong_domain" does not match integration directory "demo_bad". |
| FAIL | manifest.iot_class.valid          | manifest.json iot_class "not_a_valid_class" is not a recognized value ...            |
| WARN | diagnostics.redaction.used        | diagnostics returns entry.data without redaction — likely exposes secrets ...         |
```

The fixture intentionally triggers a range of findings across categories so you can see what actionable output looks like.

## 2. Inspect a finding

```bash
uv run hasscheck explain manifest.domain.matches_directory
```

Output shows the rule ID, severity, whether it is overridable, the `why` text, and the source URL — the same sourced information that appears in the JSON report.

## 3. Generate a fix scaffold

```bash
uv run hasscheck scaffold diagnostics --path examples/bad_integration --dry-run
```

The `--dry-run` flag prints the proposed file contents without writing. This lets you review the generated `diagnostics.py` starter before committing.

## 4. Apply the fix

Drop `--dry-run` to write files.

```bash
uv run hasscheck scaffold diagnostics --path examples/bad_integration
```

This writes `custom_components/demo_bad/diagnostics.py` with a local redaction helper pre-wired.

## 5. Re-check

```bash
uv run hasscheck check --path examples/bad_integration
```

The `diagnostics.redaction.used` finding should improve from WARN to PASS after the scaffold is applied. Other findings (like `manifest.domain.matches_directory`) remain until you fix the underlying manifest mismatch.

## 6. Wire into CI (optional)

See [README "GitHub Action"](../README.md#github-action) for the composite action. The same fixture lives in `examples/`; you can point the action at any path.
