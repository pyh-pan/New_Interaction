# New Interaction Agent Guide

## Project Purpose

New Interaction is a local macOS-first engineering prototype for camera-based hand gesture mouse control. The product direction is short-term auxiliary input and long-term mouse replacement through a commercial-grade gesture interaction system.

## Current Implementation

- Runtime entry: `src/new_interaction/app.py`
- Gesture state machine: `src/new_interaction/gestures.py`
- Camera and MediaPipe integration: `src/new_interaction/camera.py`
- Mouse event injection: `src/new_interaction/input_controller.py`
- Tests: `tests/`
- Product source of truth: `docs/prd.md`
- Architecture guide: `docs/architecture.md`
- Runbook and troubleshooting: `docs/runbook.md`

## Development Rules

- Use Python 3.11. The expected local interpreter is Homebrew Python at `/opt/homebrew/bin/python3.11`.
- Install with `.venv/bin/python -m pip install -e ".[dev]"`.
- Run tests with `.venv/bin/python -m pytest -v`.
- Keep camera frames, hand landmarks, and mouse events local. Do not add upload, telemetry, screenshot, video, or keypoint persistence without explicit product approval.
- Preserve traditional mouse/trackpad takeover behavior. Hand gesture control must never block the user from regaining control.
- Default pointer movement is relative mode, not absolute screen mapping. Keep `--movement-mode absolute` available as a debugging fallback.

## Gesture Semantics

- Default target hand is physical right hand.
- Index extended means pointer control in relative mode.
- Index relaxed means `clutch`: hand may reposition while the mouse remains still.
- Open palm hold means pause/resume; do not reuse open palm for clutch.
- Thumb-index strict pinch means click or drag. Pinch detection uses absolute distance, scaled hand distance, consecutive frames, and isolation from other fingers.
- Two-finger mode is for scrolling and must remain separate from pinch drag.

## Phase 1.5 Pointer Model

The current default pointer model is an air-trackpad style relative mapping:

- First stable frames establish a reference point and do not move the cursor.
- Relative index fingertip deltas move the current system cursor.
- Dynamic gain makes fast movement travel farther than slow movement.
- `relative_max_delta` clamps single-frame jumps to prevent camera/keypoint glitches from throwing the cursor across the screen.
- Edge cruise moves continuously when the hand stays near the comfort-zone edge.

When changing this area, keep or add tests for:

- no cursor jump on tracking start
- clutch recentering without mouse movement
- dynamic gain
- single-frame jump clamp
- edge cruise
- click/drag/scroll/pause intent separation

## Documentation Rules

- Update `README.md` when commands, setup, or user-facing gesture behavior changes.
- Update `docs/architecture.md` when data flow, state machine behavior, or module boundaries change.
- Update `docs/runbook.md` when permissions, common parameters, failure modes, or troubleshooting steps change.
- Update `docs/prd.md` for product direction and roadmap decisions, not one-off bug history.
