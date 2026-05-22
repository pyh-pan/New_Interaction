# Runbook

## Environment

Use Python 3.11 on macOS:

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

Run tests:

```bash
.venv/bin/python -m pytest -v
```

## Dry-Run Validation

Start without mouse injection:

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state --max-frames 300
```

Dry-run output should show state changes and `move-rel`, `click`, `drag-*`, `scroll`, or `pause` events.

## Real Mouse Control

Enable system input injection explicitly:

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state
```

Stop options:

- press `Ctrl+C` in the terminal.
- press `q` in the OpenCV preview window.
- move the mouse to a screen corner to trigger PyAutoGUI fail-safe.

## macOS Permissions

Camera permission is granted to the app that requests the camera. If running from Terminal:

```bash
tccutil reset Camera com.apple.Terminal
```

If running from Codex:

```bash
tccutil reset Camera com.openai.codex
```

For real mouse control, grant Accessibility permission to the terminal or app running the script:

```text
System Settings > Privacy & Security > Accessibility
```

## Recommended Phase 1.5 Command

```bash
.venv/bin/python -m new_interaction.app \
  --control \
  --show-preview \
  --debug-state \
  --movement-mode relative \
  --relative-sensitivity 1.2 \
  --relative-max-gain 2.4 \
  --relative-max-delta 0.08 \
  --relative-warmup-frames 3 \
  --edge-cruise-speed 0.006 \
  --pinch-scale-threshold 0.24 \
  --pinch-release-scale-threshold 0.45 \
  --pointer-smoothing-alpha 0.30
```

## Common Tuning

| Symptom | First adjustment |
| --- | --- |
| Cursor jumps when hand enters frame | Increase `--relative-warmup-frames` to `5`, or lower `--relative-max-delta` to `0.05` |
| Cursor too slow on a large screen | Increase `--relative-sensitivity` gradually |
| Fast movement too weak | Increase `--relative-max-gain` gradually |
| Precise clicking is difficult | Lower `--relative-min-gain` or lower `--relative-sensitivity` |
| Cursor jitters | Lower `--pointer-smoothing-alpha` toward `0.25` |
| Pinch triggers before fingers touch | Lower `--pinch-scale-threshold` |
| Drag release feels late | Lower `--pinch-release-scale-threshold` |
| Left hand or face touch triggers events | Keep `--target-hand Right`; inspect `ignored_hand` state |

## State Debugging

Important states:

- `active_move`: relative pointer movement is active.
- `clutch`: index relaxed; hand can reposition without pointer movement.
- `edge_cruise`: comfort-zone edge is held; pointer continues moving.
- `pinch_candidate`: strict pinch is being confirmed.
- `pinch_active`: pinch is held.
- `dragging`: drag is active.
- `scrolling`: two-finger scroll mode is active.
- `paused`: open palm pause is active.
- `tracking_lost`: no credible hand frame.

## Fallbacks

Return to absolute mapping for debugging:

```bash
.venv/bin/python -m new_interaction.app --control --show-preview --debug-state --movement-mode absolute
```

Disable real mouse injection and inspect event output:

```bash
.venv/bin/python -m new_interaction.app --show-preview --debug-state
```
