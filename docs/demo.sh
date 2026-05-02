#!/usr/bin/env bash
# Deterministic walkthrough of HassCheck against a copy of the bad_integration
# fixture. Used as the input for the asciinema/vhs recording in `docs/`.
#
# Run interactively to record:
#   asciinema rec --command='bash docs/demo.sh' docs/demo.cast
#
# Then convert to GIF:
#   agg --theme github-dark --speed 1.2 docs/demo.cast docs/demo.gif
#
# The script copies the tracked fixture to /tmp so scaffold writes do not
# pollute the repo. No real-user data, no secrets, no fabricated output.
set -euo pipefail

DEMO_DIR="$(mktemp -d -t hasscheck-demo.XXXXXX)"
trap 'rm -rf "${DEMO_DIR}"' EXIT

REPO_ROOT="$(git rev-parse --show-toplevel)"
cp -R "${REPO_ROOT}/examples/bad_integration/." "${DEMO_DIR}/"

# Pause helper — slow enough to read, fast enough to stay under 90 seconds.
pause() {
  sleep "${1:-1.5}"
}

cmd() {
  printf '%s\n' ''
  printf '%s\n' "\$ $*"
  pause 0.6
  "$@" || true
  pause 1.5
}

clear
printf '%s\n' 'HassCheck — local quality signals for HA custom integrations'
printf '%s\n' '------------------------------------------------------------'
pause 1.5

# 1. Initial check against the bad fixture.
cmd uv run hasscheck check --path "${DEMO_DIR}"

# 2. Explain a single finding.
cmd uv run hasscheck explain manifest.domain.matches_directory

# 3. Preview a fix scaffold.
cmd uv run hasscheck scaffold diagnostics --path "${DEMO_DIR}" --dry-run

# 4. Apply the scaffold and re-check to show movement.
cmd uv run hasscheck scaffold diagnostics --path "${DEMO_DIR}"
cmd uv run hasscheck check --path "${DEMO_DIR}"

printf '%s\n' ''
printf '%s\n' 'Done. See docs/demo.md for the full walkthrough.'
pause 2.0
