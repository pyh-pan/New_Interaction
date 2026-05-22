# Phase 1.5 Comfort Pointer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 1.5: relative pointer movement, comfort zone, clutch repositioning, dynamic gain, and edge cruise while preserving existing click, drag, scroll, and pause intent accuracy.

**Architecture:** Keep gesture intent in `src/new_interaction/gestures.py`; emit absolute pointer events for legacy mode and relative delta events for comfort mode. Keep system injection in `src/new_interaction/input_controller.py`; add relative move and drag injection without changing camera tracking.

**Tech Stack:** Python dataclasses, existing pytest suite, PyAutoGUI event injection.

---

### Task 1: Relative Pointer Events

**Files:**
- Modify: `src/new_interaction/gestures.py`
- Modify: `tests/test_gestures.py`

- [ ] Add failing tests for no-jump relative tracking, relative delta movement, and clutch reset.
- [ ] Add `movement_mode`, relative sensitivity, dynamic gain, comfort zone, and edge cruise config.
- [ ] Implement `active_move`, `clutch`, and `edge_cruise` status behavior.
- [ ] Verify targeted gesture tests pass.

### Task 2: Relative System Injection

**Files:**
- Modify: `src/new_interaction/input_controller.py`
- Modify: `tests/test_input_controller.py`

- [ ] Add failing tests for relative move, relative click at current cursor, relative drag, and drag release.
- [ ] Implement `moveRel` and `dragRel` handling for `InteractionEvent.dx/dy`.
- [ ] Preserve absolute move/click/drag behavior.
- [ ] Verify input controller tests pass.

### Task 3: CLI And Docs

**Files:**
- Modify: `src/new_interaction/app.py`
- Modify: `tests/test_app.py`
- Modify: `README.md`
- Modify: `docs/prd.md`

- [ ] Add CLI flags for movement mode, relative sensitivity, dynamic gain, comfort zone size, and edge cruise.
- [ ] Pass CLI args into `GestureConfig`.
- [ ] Update README with recommended Phase 1.5 command.
- [ ] Run full pytest and compileall.
