# MVP Engineering Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python engineering prototype that validates macOS camera access, real-time hand gesture recognition, and basic mouse interactions.

**Architecture:** Keep computer vision, gesture state, and mouse injection separate. The testable core is a pure gesture state machine; the runtime loop wires camera frames to MediaPipe landmarks and then to an input backend.

**Tech Stack:** Python 3.11, OpenCV, MediaPipe, PyAutoGUI, pytest.

---

## File Structure

- `pyproject.toml`: project metadata, dependencies, and pytest config.
- `README.md`: local setup, permission notes, and run commands.
- `src/new_interaction/__init__.py`: package marker.
- `src/new_interaction/gestures.py`: pure hand landmark model, gesture classification, and interaction state machine.
- `src/new_interaction/input_controller.py`: dry-run and PyAutoGUI mouse backends.
- `src/new_interaction/camera.py`: camera capture and MediaPipe hand landmark adapter.
- `src/new_interaction/app.py`: CLI runtime loop for the engineering validation prototype.
- `tests/test_gestures.py`: TDD coverage for click, double-click, drag, scroll, pause, and lost-hand behavior.

## Tasks

### Task 1: Gesture State Machine

**Files:**
- Create: `tests/test_gestures.py`
- Create: `src/new_interaction/gestures.py`

- [ ] Write failing tests for single click, double click, drag, scroll, pause, and hand-lost behavior.
- [ ] Run `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest tests/test_gestures.py -v` and verify the tests fail because `new_interaction.gestures` does not exist.
- [ ] Implement the minimal pure state machine in `gestures.py`.
- [ ] Run the tests again and verify they pass.

### Task 2: Input Backends

**Files:**
- Create: `src/new_interaction/input_controller.py`

- [ ] Add a dry-run backend that records or prints mouse events without controlling the system.
- [ ] Add a PyAutoGUI backend that can move, click, double-click, drag, and scroll when explicitly enabled.
- [ ] Keep dry-run as the default runtime path.

### Task 3: Camera and Hand Landmarks

**Files:**
- Create: `src/new_interaction/camera.py`

- [ ] Add OpenCV camera capture.
- [ ] Add MediaPipe Hand Landmarker integration.
- [ ] Convert MediaPipe landmarks into the pure `HandFrame` shape used by the state machine.
- [ ] Print a clear error when camera access or dependencies are missing.

### Task 4: CLI Runtime

**Files:**
- Create: `src/new_interaction/app.py`
- Create: `src/new_interaction/__init__.py`
- Create: `pyproject.toml`
- Create: `README.md`

- [ ] Add `python -m new_interaction.app` entrypoint.
- [ ] Support `--dry-run` by default and `--control` for real mouse event injection.
- [ ] Support `--camera-index`, `--show-preview`, `--max-fps`, and gesture tuning options.
- [ ] Document macOS Camera and Accessibility permissions.

### Task 5: Verification

**Files:**
- Modify as needed based on failures.

- [ ] Run tests with Python 3.11.
- [ ] Run CLI help.
- [ ] Run a dependency import check.
- [ ] If hardware access is unavailable, document the exact manual command for camera validation.

