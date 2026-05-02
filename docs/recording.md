# Recording the demo

`docs/demo.sh` is the deterministic source of truth for the visual demo. The
recording is regenerated from this script — the script is the artifact, the GIF
is the rendering. If the demo flow changes, edit `demo.sh`, re-record, commit
both.

## Prerequisites

- [`asciinema`](https://docs.asciinema.org/manual/cli/installation/) — terminal recorder.
- [`agg`](https://github.com/asciinema/agg) — converts `.cast` files to `.gif`.
- A working `uv` and the repo's tracked `examples/bad_integration` fixture.

```bash
brew install asciinema agg
```

## Record

From the repo root, in an interactive terminal:

```bash
asciinema rec \
  --idle-time-limit 2.5 \
  --command 'bash docs/demo.sh' \
  docs/demo.cast
```

`--idle-time-limit 2.5` clamps the deliberate inter-command pauses inside
`demo.sh` (3s) to 2.5s during playback while preserving the per-character
typing rhythm. The script types each command character-by-character via a
custom `typed()` helper to feel like a human at the keyboard.

The recording exits when `demo.sh` finishes. Confirm length is in the 30–90
second window per acceptance criteria from #105.

### Tuning the pacing

`docs/demo.sh` reads three env vars:

- `TYPE_DELAY` (default `0.045`) — seconds per character when typing a command
- `INTER_CMD_PAUSE` (default `3.0`) — seconds between one command's output and
  the next command's first keystroke
- `PRE_RUN_PAUSE` (default `0.8`) — seconds between finishing typing and the
  command actually running

Tweak inline before recording, e.g. `INTER_CMD_PAUSE=2.0 asciinema rec ...`
for a tighter cut.

`DEMO_FAST=1` skips the per-character sleeps entirely — used for smoke-testing
the script without recording.

## Render to GIF

```bash
agg --theme github-dark --speed 1.0 docs/demo.cast docs/demo.gif
```

Tweak `--speed` and `--theme` if the result feels too fast/slow or contrast is
off on the README's background. With the typed pacing baked into `demo.sh`,
`--speed 1.0` is usually the right default — the script does the slowing.

## Commit

```bash
git add docs/demo.sh docs/demo.cast docs/demo.gif docs/recording.md
git commit -m "docs(demo): record terminal demo (#105)"
```

Both the `.cast` (replayable, lightweight) and the `.gif` (universally
renderable on GitHub) are checked in.

## Embed in README

The README "See it in action" section already reserves the slot. Add the
embed once the GIF is committed:

```md
![HassCheck demo](docs/demo.gif)
```

If you also want an asciinema-player embed, host the `.cast` on
[asciinema.org](https://asciinema.org/) and paste the iframe — purely
optional; the GIF works everywhere GitHub does.

## Rules of thumb

- **No real-user data.** The script runs against a `/tmp/` copy of the tracked
  `bad_integration` fixture; nothing personal.
- **No fabricated output.** Whatever HassCheck prints is what gets recorded.
- **No "certified / approved / safe" language** in any caption or alt text.
- **Regenerable.** A reviewer must be able to run the same `asciinema rec`
  command and get a functionally identical recording.
