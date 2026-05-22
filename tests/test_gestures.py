from dataclasses import replace

import pytest

from new_interaction.gestures import GestureConfig, GestureStateMachine, HandFrame, Point


def make_frame(
    *,
    x: float = 0.5,
    y: float = 0.5,
    pinched: bool = False,
    clustered: bool = False,
    scroll: bool = False,
    open_palm: bool = False,
    handedness: str = "Right",
) -> HandFrame:
    landmarks = {
        0: Point(x, y + 0.25),
        4: Point(x - (0.01 if pinched else 0.20), y),
        5: Point(x, y + 0.12),
        6: Point(x, y + 0.06),
        8: Point(x, y),
        9: Point(x + 0.08, y + 0.12),
        10: Point(x + 0.08, y + 0.06),
        12: Point(x + 0.08, y + (0.01 if scroll else 0.18)),
        13: Point(x + 0.16, y + 0.12),
        14: Point(x + 0.16, y + (0.06 if open_palm else -0.02)),
        16: Point(x + 0.16, y + (0.00 if open_palm else 0.18)),
        17: Point(x + 0.24, y + 0.12),
        18: Point(x + 0.24, y + (0.06 if open_palm else -0.02)),
        20: Point(x + 0.24, y + (0.00 if open_palm else 0.18)),
    }
    if scroll:
        landmarks[16] = Point(x + 0.16, y + 0.20)
        landmarks[20] = Point(x + 0.24, y + 0.20)
    if open_palm:
        landmarks[4] = Point(x - 0.25, y + 0.04)
        landmarks[8] = Point(x, y - 0.12)
        landmarks[12] = Point(x + 0.08, y - 0.12)
    if clustered:
        landmarks[4] = Point(x - 0.01, y)
        landmarks[8] = Point(x, y)
        landmarks[12] = Point(x + 0.01, y)
        landmarks[16] = Point(x + 0.02, y)
        landmarks[20] = Point(x + 0.03, y)
    return HandFrame(landmarks=landmarks, handedness=handedness, confidence=0.95)


def machine() -> GestureStateMachine:
    return GestureStateMachine(
        GestureConfig(
            pinch_threshold=0.06,
            pinch_release_threshold=0.09,
            pinch_release_scale_threshold=0.45,
            pinch_confirm_frames=2,
            drag_hold_seconds=0.35,
            double_click_window_seconds=0.35,
            pause_hold_seconds=0.30,
            scroll_sensitivity=1000,
            pointer_smoothing_alpha=1.0,
            movement_mode="absolute",
            target_handedness="Right",
        )
    )


def confirm_pinch(sm: GestureStateMachine, *, timestamp: float, x: float = 0.5) -> None:
    sm.update(make_frame(x=x), timestamp=timestamp - 0.10)
    sm.update(make_frame(pinched=True, x=x), timestamp=timestamp)
    sm.update(make_frame(pinched=True, x=x), timestamp=timestamp + 0.03)


def test_short_pinch_release_emits_single_click():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    events = sm.update(make_frame(pinched=False), timestamp=1.10)

    assert [(event.kind, event.click_count) for event in events] == [("click", 1)]


def test_click_uses_hover_anchor_before_pinch_moves_index_finger():
    sm = machine()

    sm.update(make_frame(x=0.40), timestamp=1.00)
    sm.update(make_frame(pinched=True, x=0.48), timestamp=1.05)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.08)
    events = sm.update(make_frame(x=0.52), timestamp=1.13)

    assert [(event.kind, event.position.x) for event in events] == [("click", 0.40)]


def test_two_quick_short_pinches_marks_second_click_as_double_click():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=False), timestamp=1.08)
    confirm_pinch(sm, timestamp=1.20)
    events = sm.update(make_frame(pinched=False), timestamp=1.28)

    assert [(event.kind, event.click_count) for event in events] == [("click", 2)]


def test_holding_pinch_enters_drag_until_release():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00, x=0.40)
    start_events = sm.update(make_frame(pinched=True, x=0.42), timestamp=1.40)
    move_events = sm.update(make_frame(pinched=True, x=0.45), timestamp=1.50)
    end_events = sm.update(make_frame(pinched=False, x=0.45), timestamp=1.60)

    assert [event.kind for event in start_events] == ["drag_start"]
    assert [event.kind for event in move_events] == ["drag_move"]
    assert [event.kind for event in end_events] == ["drag_end"]


def test_drag_releases_immediately_when_pinch_opens_past_scaled_release_threshold():
    sm = machine()
    opened = make_frame(pinched=True, x=0.45)
    opened.landmarks[4] = Point(0.38, 0.50)
    opened.landmarks[8] = Point(0.45, 0.50)

    confirm_pinch(sm, timestamp=1.00, x=0.40)
    sm.update(make_frame(pinched=True, x=0.42), timestamp=1.40)
    events = sm.update(opened, timestamp=1.43)

    assert [event.kind for event in events] == ["drag_end"]
    assert sm.status.state == "drag_end"


def test_drag_starts_at_hover_anchor_and_then_uses_relative_motion():
    sm = machine()

    sm.update(make_frame(x=0.40), timestamp=1.00)
    sm.update(make_frame(pinched=True, x=0.46), timestamp=1.05)
    sm.update(make_frame(pinched=True, x=0.48), timestamp=1.08)
    start_events = sm.update(make_frame(pinched=True, x=0.48), timestamp=1.45)
    move_events = sm.update(make_frame(pinched=True, x=0.53), timestamp=1.55)

    assert [(event.kind, event.position.x) for event in start_events] == [("drag_start", 0.40)]
    assert [(event.kind, round(event.position.x, 2)) for event in move_events] == [
        ("drag_move", 0.45)
    ]


def test_pointer_motion_is_smoothed_between_frames():
    sm = GestureStateMachine(
        GestureConfig(
            pointer_smoothing_alpha=0.25,
            movement_mode="absolute",
            target_handedness="Right",
        )
    )

    first = sm.update(make_frame(x=0.50), timestamp=1.00)
    second = sm.update(make_frame(x=0.70), timestamp=1.03)
    third = sm.update(make_frame(x=0.50), timestamp=1.06)

    assert first[0].position == Point(0.50, 0.50)
    assert second[0].position == Point(0.55, 0.50)
    assert third[0].position.x == pytest.approx(0.5375)
    assert third[0].position.y == 0.50


def test_drag_motion_uses_smoothed_relative_pointer():
    sm = GestureStateMachine(
        GestureConfig(
            pinch_threshold=0.06,
            pinch_release_threshold=0.09,
            pinch_release_scale_threshold=0.45,
            pinch_confirm_frames=2,
            drag_hold_seconds=0.35,
            pointer_smoothing_alpha=0.50,
            movement_mode="absolute",
            target_handedness="Right",
        )
    )

    sm.update(make_frame(x=0.40), timestamp=1.00)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.05)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.08)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.45)
    events = sm.update(make_frame(pinched=True, x=0.70), timestamp=1.50)

    assert [(event.kind, round(event.position.x, 3)) for event in events] == [
        ("drag_move", 0.5)
    ]


def relative_machine() -> GestureStateMachine:
    return GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pointer_smoothing_alpha=1.0,
            relative_sensitivity=1.0,
            relative_min_gain=1.0,
            relative_max_gain=1.0,
            relative_gain_motion_threshold=0.10,
            comfort_zone_width=0.40,
            comfort_zone_height=0.40,
            edge_cruise_margin=0.15,
            edge_cruise_speed=0.02,
            relative_warmup_frames=1,
            relative_max_delta=0.08,
            target_handedness="Right",
        )
    )


def relaxed_frame(*, x: float = 0.5, y: float = 0.5) -> HandFrame:
    frame = make_frame(x=x, y=y)
    frame.landmarks[8] = Point(x, y + 0.10)
    return frame


def test_relative_mode_does_not_jump_when_tracking_starts():
    sm = relative_machine()

    events = sm.update(make_frame(x=0.60), timestamp=1.00)

    assert events == []
    assert sm.status.state == "active_move"


def test_relative_mode_waits_for_warmup_frames_before_moving():
    sm = GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pointer_smoothing_alpha=1.0,
            relative_warmup_frames=3,
            target_handedness="Right",
        )
    )

    first = sm.update(make_frame(x=0.10), timestamp=1.00)
    second = sm.update(make_frame(x=0.80), timestamp=1.03)
    third = sm.update(make_frame(x=0.82), timestamp=1.06)
    move = sm.update(make_frame(x=0.83), timestamp=1.09)

    assert first == []
    assert second == []
    assert third == []
    assert [(event.kind, event.dx > 0, abs(event.dx) < 0.10) for event in move] == [
        ("move", True, True)
    ]


def test_relative_mode_recenter_after_clutch_prevents_edge_cruise_drift():
    sm = relative_machine()

    sm.update(make_frame(x=0.50), timestamp=1.00)
    sm.update(make_frame(x=0.55), timestamp=1.03)
    sm.update(relaxed_frame(x=0.20), timestamp=1.06)
    resume = sm.update(make_frame(x=0.90), timestamp=1.09)
    steady = sm.update(make_frame(x=0.90), timestamp=1.12)

    assert resume == []
    assert steady == []
    assert sm.status.state == "active_move"


def test_relative_mode_emits_pointer_delta_after_reference_is_established():
    sm = relative_machine()

    sm.update(make_frame(x=0.50, y=0.50), timestamp=1.00)
    events = sm.update(make_frame(x=0.55, y=0.47), timestamp=1.03)

    assert [(event.kind, event.position, event.dx, event.dy) for event in events] == [
        ("move", None, pytest.approx(0.05), pytest.approx(-0.03))
    ]


def test_relative_mode_clutch_lets_hand_reposition_without_moving_pointer():
    sm = relative_machine()

    sm.update(make_frame(x=0.50), timestamp=1.00)
    sm.update(make_frame(x=0.55), timestamp=1.03)
    clutch_events = sm.update(relaxed_frame(x=0.30), timestamp=1.06)
    resume_events = sm.update(make_frame(x=0.30), timestamp=1.09)
    move_events = sm.update(make_frame(x=0.35), timestamp=1.12)

    assert clutch_events == []
    assert resume_events == []
    assert sm.status.state == "active_move"
    assert [(event.kind, event.dx, event.dy) for event in move_events] == [
        ("move", pytest.approx(0.05), pytest.approx(0.0))
    ]


def test_relative_mode_dynamic_gain_amplifies_fast_motion():
    sm = GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pointer_smoothing_alpha=1.0,
            relative_sensitivity=1.0,
            relative_min_gain=1.0,
            relative_max_gain=3.0,
            relative_gain_motion_threshold=0.10,
            relative_warmup_frames=1,
            relative_max_delta=1.0,
            edge_cruise_speed=0.0,
            target_handedness="Right",
        )
    )

    sm.update(make_frame(x=0.50), timestamp=1.00)
    slow = sm.update(make_frame(x=0.52), timestamp=1.03)
    fast = sm.update(make_frame(x=0.62), timestamp=1.06)

    assert slow[0].dx == pytest.approx(0.028)
    assert fast[0].dx == pytest.approx(0.30)


def test_relative_mode_clamps_single_frame_jump_after_gain():
    sm = GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pointer_smoothing_alpha=1.0,
            relative_warmup_frames=1,
            relative_sensitivity=3.0,
            relative_min_gain=1.0,
            relative_max_gain=4.0,
            relative_max_delta=0.08,
            edge_cruise_speed=0.0,
            target_handedness="Right",
        )
    )

    sm.update(make_frame(x=0.50), timestamp=1.00)
    events = sm.update(make_frame(x=0.95), timestamp=1.03)

    assert [(event.kind, event.dx, event.dy) for event in events] == [
        ("move", pytest.approx(0.08), pytest.approx(0.0))
    ]


def test_relative_mode_edge_cruise_continues_at_comfort_zone_edge():
    sm = relative_machine()

    sm.update(make_frame(x=0.50), timestamp=1.00)
    first = sm.update(make_frame(x=0.68), timestamp=1.03)
    second = sm.update(make_frame(x=0.68), timestamp=1.06)

    assert first[0].dx == pytest.approx(0.09)
    assert [(event.kind, event.dx, event.dy) for event in second] == [
        ("move", pytest.approx(0.01), pytest.approx(0.0))
    ]


def test_relative_mode_short_pinch_clicks_current_pointer_without_absolute_position():
    sm = GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pinch_threshold=0.06,
            pinch_release_threshold=0.09,
            pinch_release_scale_threshold=0.45,
            pinch_confirm_frames=2,
            drag_hold_seconds=0.35,
            pointer_smoothing_alpha=1.0,
            target_handedness="Right",
        )
    )

    sm.update(make_frame(x=0.50), timestamp=1.00)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.05)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.08)
    events = sm.update(make_frame(pinched=False, x=0.50), timestamp=1.12)

    assert [(event.kind, event.position, event.click_count) for event in events] == [
        ("click", None, 1)
    ]


def test_relative_mode_drag_uses_relative_delta_without_absolute_position():
    sm = GestureStateMachine(
        GestureConfig(
            movement_mode="relative",
            pinch_threshold=0.06,
            pinch_release_threshold=0.09,
            pinch_release_scale_threshold=0.45,
            pinch_confirm_frames=2,
            drag_hold_seconds=0.35,
            pointer_smoothing_alpha=1.0,
            relative_sensitivity=1.0,
            relative_min_gain=1.0,
            relative_max_gain=1.0,
            edge_cruise_speed=0.0,
            target_handedness="Right",
        )
    )

    sm.update(make_frame(x=0.50), timestamp=1.00)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.05)
    sm.update(make_frame(pinched=True, x=0.50), timestamp=1.08)
    start = sm.update(make_frame(pinched=True, x=0.50), timestamp=1.45)
    move = sm.update(make_frame(pinched=True, x=0.56), timestamp=1.48)

    assert [(event.kind, event.position) for event in start] == [("drag_start", None)]
    assert [(event.kind, event.position, event.dx, event.dy) for event in move] == [
        ("drag_move", None, pytest.approx(0.06), pytest.approx(0.0))
    ]


def test_two_finger_scroll_does_not_emit_pointer_move():
    sm = machine()

    sm.update(make_frame(scroll=True, y=0.50), timestamp=1.00)
    events = sm.update(make_frame(scroll=True, y=0.45), timestamp=1.05)

    assert [event.kind for event in events] == ["scroll"]
    assert events[0].dy > 0


def test_scroll_between_clicks_clears_pending_double_click_window():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=False), timestamp=1.08)
    sm.update(make_frame(scroll=True, y=0.50), timestamp=1.12)
    sm.update(make_frame(scroll=True, y=0.45), timestamp=1.16)
    confirm_pinch(sm, timestamp=1.22)
    events = sm.update(make_frame(pinched=False), timestamp=1.30)

    assert [(event.kind, event.click_count) for event in events] == [("click", 1)]


def test_open_palm_hold_toggles_pause_and_suppresses_motion():
    sm = machine()

    sm.update(make_frame(open_palm=True), timestamp=1.00)
    pause_events = sm.update(make_frame(open_palm=True), timestamp=1.35)
    move_events = sm.update(make_frame(x=0.90), timestamp=1.45)

    assert [(event.kind, event.paused) for event in pause_events] == [("pause_changed", True)]
    assert move_events == []
    assert sm.paused is True


def test_pause_candidate_clears_scroll_anchor_before_resuming_scroll():
    sm = machine()

    sm.update(make_frame(scroll=True, y=0.50), timestamp=1.00)
    sm.update(make_frame(open_palm=True), timestamp=1.05)
    events = sm.update(make_frame(scroll=True, y=0.20), timestamp=1.10)

    assert events == []


def test_pause_toggle_clears_scroll_anchor_before_resuming_scroll():
    sm = machine()

    sm.update(make_frame(scroll=True, y=0.50), timestamp=1.00)
    sm.update(make_frame(open_palm=True), timestamp=1.05)
    sm.update(make_frame(open_palm=True), timestamp=1.40)
    sm.update(make_frame(), timestamp=1.45)
    sm.update(make_frame(open_palm=True), timestamp=1.50)
    sm.update(make_frame(open_palm=True), timestamp=1.85)
    events = sm.update(make_frame(scroll=True, y=0.20), timestamp=1.90)

    assert events == []


def test_lost_hand_ends_active_drag():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=True), timestamp=1.40)
    events = sm.update(None, timestamp=1.45)

    assert [event.kind for event in events] == ["drag_end", "tracking_lost"]


def test_left_hand_is_ignored_and_does_not_emit_move_or_click():
    sm = machine()

    sm.update(make_frame(handedness="Left"), timestamp=1.00)
    sm.update(make_frame(pinched=True, handedness="Left"), timestamp=1.05)
    events = sm.update(make_frame(handedness="Left"), timestamp=1.10)

    assert events == []
    assert sm.status.state == "ignored_hand"


def test_single_frame_pinch_noise_does_not_click():
    sm = machine()

    sm.update(make_frame(), timestamp=1.00)
    sm.update(make_frame(pinched=True), timestamp=1.05)
    events = sm.update(make_frame(), timestamp=1.10)

    assert [event.kind for event in events] == ["move"]
    assert sm.status.state == "move"


def test_clustered_fingertips_do_not_count_as_strict_pinch():
    sm = machine()

    sm.update(make_frame(), timestamp=1.00)
    sm.update(make_frame(clustered=True), timestamp=1.05)
    events = sm.update(make_frame(), timestamp=1.10)

    assert [event.kind for event in events] == ["move"]
    assert sm.status.state == "move"


def test_partial_pinch_below_absolute_threshold_does_not_activate():
    sm = machine()
    partial = make_frame()
    partial.landmarks[4] = Point(0.45, 0.50)
    partial.landmarks[8] = Point(0.50, 0.50)

    sm.update(make_frame(), timestamp=1.00)
    sm.update(partial, timestamp=1.05)
    events = sm.update(partial, timestamp=1.08)

    assert [event.kind for event in events] == ["move"]
    assert sm.status.state == "move"
    assert sm.status.pinch_scaled_distance is not None
    assert sm.status.pinch_scaled_distance > sm.config.pinch_scale_threshold


def test_pinch_uses_palm_scale_when_finger_length_is_foreshortened():
    sm = machine()
    pinched = make_frame(pinched=True)
    pinched.landmarks[4] = Point(0.475, 0.50)
    pinched.landmarks[5] = Point(0.49, 0.50)
    pinched.landmarks[8] = Point(0.50, 0.50)
    pinched.landmarks[9] = Point(0.58, 0.62)
    pinched.landmarks[17] = Point(0.55, 0.50)

    sm.update(make_frame(), timestamp=1.00)
    sm.update(pinched, timestamp=1.05)
    sm.update(pinched, timestamp=1.08)

    assert sm.status.state == "pinch_active"
    assert sm.status.pinch_scaled_distance is not None
    assert sm.status.pinch_scaled_distance <= sm.config.pinch_scale_threshold


def test_pinch_hysteresis_keeps_contact_while_scaled_distance_stays_near_contact():
    sm = machine()
    nearly_released = make_frame(pinched=True)
    nearly_released.landmarks[4] = Point(0.455, 0.50)
    nearly_released.landmarks[8] = Point(0.50, 0.50)

    confirm_pinch(sm, timestamp=1.00)
    events = sm.update(nearly_released, timestamp=1.08)

    assert events == []
    assert sm.status.state == "pinch_active"


def test_pinch_candidate_does_not_emit_move_or_overwrite_status():
    sm = machine()

    sm.update(make_frame(), timestamp=1.00)
    events = sm.update(make_frame(pinched=True), timestamp=1.05)

    assert events == []
    assert sm.status.state == "pinch_candidate"
    assert sm.status.reason == "waiting for consecutive pinch frames"


def test_pinch_blocked_does_not_emit_move_or_overwrite_status():
    sm = machine()

    events = sm.update(make_frame(pinched=True), timestamp=1.00)

    assert events == []
    assert sm.status.state == "pinch_blocked"
    assert sm.status.reason == "waiting for open hand before pinch"


def test_lost_tracking_clears_pending_double_click_window():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=False), timestamp=1.08)
    sm.update(None, timestamp=1.12)
    confirm_pinch(sm, timestamp=1.20)
    events = sm.update(make_frame(pinched=False), timestamp=1.28)

    assert [(event.kind, event.click_count) for event in events] == [("click", 1)]


def test_ignored_hand_clears_pending_double_click_window():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=False), timestamp=1.08)
    sm.update(make_frame(handedness="Left"), timestamp=1.12)
    confirm_pinch(sm, timestamp=1.20)
    events = sm.update(make_frame(pinched=False), timestamp=1.28)

    assert [(event.kind, event.click_count) for event in events] == [("click", 1)]


def test_low_confidence_clears_pending_double_click_window():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    sm.update(make_frame(pinched=False), timestamp=1.08)
    sm.update(replace(make_frame(), confidence=0.20), timestamp=1.12)
    confirm_pinch(sm, timestamp=1.20)
    events = sm.update(make_frame(pinched=False), timestamp=1.28)

    assert [(event.kind, event.click_count) for event in events] == [("click", 1)]


def test_open_palm_after_active_pinch_cancels_without_clicking():
    sm = machine()

    confirm_pinch(sm, timestamp=1.00)
    events = sm.update(make_frame(open_palm=True), timestamp=1.10)

    assert events == []
    assert sm.status.state == "pause_candidate"
    assert sm.status.reason == "open palm canceled active pinch"
