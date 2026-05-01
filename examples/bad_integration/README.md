# bad_integration fixture

This directory is an **intentionally broken** Home Assistant integration used by hasscheck's own test suite to demonstrate failing rules.

It is NOT a real integration. Every defect is deliberate. Run `hasscheck check examples/bad_integration` to see the full findings list.

## Intentional defects (v0.8)

- `manifest.json` declares `"domain": "wrong_domain"` but the directory is `demo_bad` — triggers **manifest.domain.matches_directory** FAIL.
- `manifest.json` declares `"iot_class": "not_a_valid_class"` — triggers **manifest.iot_class.valid** FAIL (PR2).
- `manifest.json` omits `integration_type` — triggers **manifest.integration_type.exists** WARN (PR2).
- `config_flow.py` defines `async_step_setup` instead of `async_step_user` — triggers **config_flow.user_step.exists** WARN (PR3).
- `diagnostics.py` returns `entry.data` without redaction — triggers **diagnostics.redaction.used** WARN (PR4).

Additional defects will be added as new rules land in subsequent PRs.
