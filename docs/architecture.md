# Architecture

## Overview

New Interaction is a local camera-to-mouse pipeline:

```text
macOS camera
  -> OpenCV frame capture
  -> MediaPipe Hand Landmarker
  -> HandFrame landmarks
  -> GestureStateMachine
  -> InteractionEvent
  -> DryRunInputController or PyAutoGUIInputController
  -> macOS mouse events
```

The current prototype is intentionally rule-based. It validates interaction design, permission behavior, and mouse injection before the product moves into data collection or model training.

## Modules

| File | Responsibility |
| --- | --- |
| `src/new_interaction/app.py` | CLI parsing, config assembly, camera loop, debug-state printing |
| `src/new_interaction/camera.py` | OpenCV camera access, MediaPipe hand detection, handedness normalization |
| `src/new_interaction/gestures.py` | Gesture state machine and interaction event generation |
| `src/new_interaction/input_controller.py` | Dry-run logging and PyAutoGUI mouse event injection |
| `tests/` | Unit tests for CLI parsing, camera conversion, gesture state, and input injection |

## Data Model

`HandFrame` is the normalized input to the gesture state machine:

- `landmarks`: MediaPipe's 21 hand landmarks mapped to normalized `Point(x, y)`.
- `handedness`: physical hand label after mirrored-camera correction.
- `confidence`: detection confidence.

`InteractionEvent` is the output contract:

- absolute pointer events use `position`.
- relative pointer events use `dx` and `dy`.
- click events carry `click_count`.
- pause events carry `paused`.

## Gesture State Machine

The state machine enforces intent separation before mouse events are emitted.

Core states:

- `active_move`: relative pointer movement is active.
- `clutch`: index is relaxed; hand may reposition without cursor movement.
- `edge_cruise`: hand is held near the comfort-zone edge; cursor continues in that direction.
- `pinch_candidate`: strict pinch is being confirmed across consecutive frames.
- `pinch_active`: strict pinch is held but not yet dragging.
- `dragging`: pinch has been held beyond the drag threshold.
- `scrolling`: two-finger scroll mode is active.
- `paused`: open-palm pause is active.
- `ignored_hand`: detected hand is not the configured target hand.
- `tracking_lost`: no credible hand is visible.

## Pointer Mapping

The default movement mode is `relative`.

Relative mode behaves like an air trackpad:

- first stable frames establish reference and comfort-zone center.
- index fingertip movement emits normalized deltas.
- index relaxed enters clutch and resets the reference on resume.
- dynamic gain scales faster motions more strongly than slow motions.
- `relative_max_delta` clamps single-frame jumps.
- edge cruise adds a small continuous delta near comfort-zone edges.

Absolute mode remains available with `--movement-mode absolute` for debugging. In absolute mode, normalized fingertip position maps directly to screen coordinates.

## Pinch And Drag

Pinch is intentionally conservative:

- absolute thumb-index distance must be below `pinch_threshold`.
- scaled thumb-index distance must be below `pinch_scale_threshold`.
- distance must remain isolated from middle finger clustering.
- multiple consecutive frames are required before activation.
- release threshold is separate from entry threshold.

In relative mode, click and drag happen at the current system cursor location. In absolute mode, click and drag use a hover anchor so the pinch motion itself does not move the click target.

## Input Injection

`PyAutoGUIInputController` injects mouse events only after `--control` is set.

- absolute move uses `moveTo`.
- relative move uses `moveRel` or a fallback based on current position.
- macOS drag uses `dragTo` or `dragRel` with `button="left"` and `mouseDownUp=False`.
- user mouse takeover is detected by comparing current pointer position to the last injected position.
- `tracking_lost` and `pause_changed` rearm takeover suppression.

## Safety Boundaries

- The app defaults to dry-run mode and only prints events.
- Real input injection requires explicit `--control`.
- PyAutoGUI fail-safe remains enabled; moving the pointer to a screen corner can stop runaway control.
- Low confidence, non-target hand, ignored hand, and lost tracking do not inject high-risk events.
- Camera data is processed locally. The current prototype does not persist video, screenshots, hand landmarks, or telemetry.
