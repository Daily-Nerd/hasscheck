#!/usr/bin/env bash
# Deterministic walkthrough of HassCheck against a copy of the bad_integration
# fixture. Used as the input for the asciinema recording in `docs/`.
#
# Run interactively to record:
#   asciinema rec --idle-time-limit 2.5 --command 'bash docs/demo.sh' docs/demo.cast
#
# Then convert to GIF:
#   agg --theme github-dark --speed 1.0 docs/demo.cast docs/demo.gif
#
# The script copies the tracked fixture to /tmp so scaffold writes do not
# pollute the repo. No real-user data, no secrets, no fabricated output.
set -euo pipefail

DEMO_DIR="$(mktemp -d -t hasscheck-demo.XXXXXX)"
trap 'rm -rf "${DEMO_DIR}"' EXIT

REPO_ROOT="$(git rev-parse --show-toplevel)"
cp -R "${REPO_ROOT}/examples/bad_integration/." "${DEMO_DIR}/"

# Per-character typing speed. 0.045s/char ≈ 22 chars/sec — fast typist feel.
_TYPE_DELAY="${TYPE_DELAY:-0.045}"
# Pause between command output finishing and the next command starting to type.
_INTER_CMD_PAUSE="${INTER_CMD_PAUSE:-3.0}"
# Pause after typing a command before it actually runs.
_PRE_RUN_PAUSE="${PRE_RUN_PAUSE:-0.8}"

pause() {
  sleep "${1}"
}

# Print a string character-by-character to mimic typing. Skips no-op sleeps
# when DEMO_FAST=1 is set (useful for smoke-testing the script).
type_str() {
  local s="$*"
  if [[ "${DEMO_FAST:-0}" == "1" ]]; then
    printf '%s' "${s}"
    return
  fi
  local i
  for ((i = 0; i < ${#s}; i++)); do
    printf '%s' "${s:i:1}"
    sleep "${_TYPE_DELAY}"
  done
}

# Print a typed prompt + command, pause briefly, then run the command for real.
typed() {
  printf '%s' '$ '
  type_str "$*"
  printf '\n'
  pause "${_PRE_RUN_PAUSE}"
  "$@" || true
  pause "${_INTER_CMD_PAUSE}"
}

clear
printf '%s\n' 'HassCheck — local quality signals for HA custom integrations'
printf '%s\n' '------------------------------------------------------------'
pause 2.0

# 1. Initial check against the bad fixture.
typed uv run hasscheck check --path "${DEMO_DIR}"

# 2. Explain a single finding.
typed uv run hasscheck explain manifest.domain.matches_directory

# 3. Preview a fix scaffold.
typed uv run hasscheck scaffold diagnostics --path "${DEMO_DIR}" --dry-run

# 4. Apply the scaffold and re-check to show movement.
# --force: bad_integration fixture ships an intentionally-unsafe diagnostics.py
# to demonstrate the diagnostics.redaction.used WARN. The scaffold rewrites it
# with a redacted variant.
typed uv run hasscheck scaffold diagnostics --path "${DEMO_DIR}" --force
typed uv run hasscheck check --path "${DEMO_DIR}"

printf '%s\n' ''
printf '%s\n' 'Done. See docs/demo.md for the full walkthrough.'
pause 2.5
