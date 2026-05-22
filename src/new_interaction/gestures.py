from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class HandFrame:
    landmarks: dict[int, Point]
    handedness: str
    confidence: float


@dataclass(frozen=True)
class GestureConfig:
    pinch_threshold: float = 0.055
    pinch_release_threshold: float = 0.085
    pinch_scale_threshold: float = 0.30
    pinch_release_scale_threshold: float = 0.45
    pinch_confirm_frames: int = 3
    pinch_isolation_distance: float = 0.040
    drag_hold_seconds: float = 0.35
    double_click_window_seconds: float = 0.35
    pause_hold_seconds: float = 0.45
    scroll_sensitivity: float = 900.0
    pointer_smoothing_alpha: float = 0.35
    movement_mode: str = "relative"
    relative_sensitivity: float = 1.20
    relative_min_gain: float = 0.80
    relative_max_gain: float = 2.40
    relative_gain_motion_threshold: float = 0.08
    relative_max_delta: float = 0.08
    comfort_zone_width: float = 0.36
    comfort_zone_height: float = 0.30
    edge_cruise_margin: float = 0.15
    edge_cruise_speed: float = 0.006
    relative_warmup_frames: int = 3
    min_confidence: float = 0.50
    target_handedness: str = "Right"


@dataclass(frozen=True)
class GestureStatus:
    state: str = "idle"
    handedness: str | None = None
    confidence: float = 0.0
    pinch_distance: float | None = None
    pinch_scaled_distance: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class InteractionEvent:
    kind: str
    position: Point | None = None
    dx: float = 0.0
    dy: float = 0.0
    click_count: int = 0
    paused: bool | None = None


class GestureStateMachine:
    def __init__(self, config: GestureConfig | None = None) -> None:
        self.config = config or GestureConfig()
        self.paused = False
        self._pinching = False
        self._pinch_started_at: float | None = None
        self._dragging = False
        self._last_click_at: float | None = None
        self._scrolling = False
        self._last_scroll_point: Point | None = None
        self._open_palm_started_at: float | None = None
        self._pause_toggle_armed = True
        self._tracking = False
        self._pinch_candidate_frames = 0
        self._pinch_candidate_started_at: float | None = None
        self._pinch_armed = False
        self._last_hover_pointer: Point | None = None
        self._pinch_anchor: Point | None = None
        self._drag_reference_pointer: Point | None = None
        self._smoothed_pointer: Point | None = None
        self._smoothed_drag_pointer: Point | None = None
        self._relative_reference_pointer: Point | None = None
        self._comfort_center: Point | None = None
        self._relative_warmup_remaining = self.config.relative_warmup_frames
        self.status = GestureStatus()

    def update(self, frame: HandFrame | None, *, timestamp: float) -> list[InteractionEvent]:
        if frame is None or frame.confidence < self.config.min_confidence:
            return self._handle_lost_tracking()

        events: list[InteractionEvent] = []
        if not self._is_target_hand(frame):
            return self._handle_ignored_hand(frame)

        self._tracking = True

        if self._is_open_palm(frame):
            self._clear_scroll_state()
            self._clear_pending_double_click()
            if self._open_palm_started_at is None:
                self._open_palm_started_at = timestamp
                self._pause_toggle_armed = True
            if self._pinching or self._dragging:
                if self._dragging:
                    events.append(InteractionEvent("drag_end"))
                self._cancel_active_pinch()
                self._set_status(frame, "pause_candidate", "open palm canceled active pinch")
                return events
            elif (
                self._pause_toggle_armed
                and timestamp - self._open_palm_started_at >= self.config.pause_hold_seconds
            ):
                self.paused = not self.paused
                self._pause_toggle_armed = False
                events.append(InteractionEvent("pause_changed", paused=self.paused))
                self._set_status(frame, "paused" if self.paused else "move", "open palm toggled pause")
            if self.paused:
                self._set_status(frame, "paused", "open palm pause is active")
                return events
            self._set_status(frame, "pause_candidate", "open palm pause candidate")
            return events
        else:
            self._open_palm_started_at = None
            self._pause_toggle_armed = True

        if self.paused:
            self._clear_scroll_state()
            self._clear_pending_double_click()
            self._set_status(frame, "paused", "paused")
            return events

        if self._is_scroll_mode(frame):
            return self._handle_scroll(frame)

        self._clear_scroll_state()

        if self._is_pinch_contact(frame):
            return self._handle_pinch_contact(frame, timestamp)
        else:
            release_events = self._handle_pinch_released(frame, timestamp)
            if release_events:
                return release_events

        if not self._pinching and not self._dragging:
            if self._relative_mode():
                return self._handle_relative_move(frame)
            self._set_status(frame, "move", "pointer follows index fingertip")
            pointer = self._smooth_pointer(self._pointer(frame))
            self._last_hover_pointer = pointer
            events.append(InteractionEvent("move", position=pointer))

        return events

    def _handle_lost_tracking(self) -> list[InteractionEvent]:
        events: list[InteractionEvent] = []
        if self._dragging:
            events.append(InteractionEvent("drag_end"))
        if self._tracking:
            events.append(InteractionEvent("tracking_lost"))
        self._tracking = False
        self._pinching = False
        self._pinch_started_at = None
        self._dragging = False
        self._clear_scroll_state()
        self._open_palm_started_at = None
        self._pause_toggle_armed = True
        self._pinch_candidate_frames = 0
        self._pinch_candidate_started_at = None
        self._pinch_armed = False
        self._last_click_at = None
        self._last_hover_pointer = None
        self._pinch_anchor = None
        self._drag_reference_pointer = None
        self._clear_relative_state()
        self._reset_smoothing()
        self.status = GestureStatus(state="tracking_lost", reason="no hand or low confidence")
        return events

    def _handle_ignored_hand(self, frame: HandFrame) -> list[InteractionEvent]:
        events: list[InteractionEvent] = []
        if self._dragging:
            events.append(InteractionEvent("drag_end"))
        self._tracking = False
        self._pinching = False
        self._pinch_started_at = None
        self._dragging = False
        self._clear_scroll_state()
        self._pinch_candidate_frames = 0
        self._pinch_candidate_started_at = None
        self._pinch_armed = False
        self._last_click_at = None
        self._last_hover_pointer = None
        self._pinch_anchor = None
        self._drag_reference_pointer = None
        self._clear_relative_state()
        self._reset_smoothing()
        self._set_status(frame, "ignored_hand", f"target hand is {self.config.target_handedness}")
        return events

    def _handle_pinch_contact(self, frame: HandFrame, timestamp: float) -> list[InteractionEvent]:
        if not self._pinching:
            if not self._pinch_armed:
                self._set_status(frame, "pinch_blocked", "waiting for open hand before pinch")
                return []
            self._pinch_candidate_frames += 1
            if self._pinch_candidate_started_at is None:
                self._pinch_candidate_started_at = timestamp
                self._pinch_anchor = self._last_hover_pointer or self._pointer(frame)
            if self._pinch_candidate_frames < self.config.pinch_confirm_frames:
                self._set_status(frame, "pinch_candidate", "waiting for consecutive pinch frames")
                return []
            self._pinching = True
            self._pinch_started_at = self._pinch_candidate_started_at or timestamp
            self._drag_reference_pointer = self._pointer(frame)
            self._set_status(frame, "pinch_active", "strict pinch confirmed")
            self._pinch_armed = False
            return []

        if (
            not self._dragging
            and self._pinch_started_at is not None
            and timestamp - self._pinch_started_at >= self.config.drag_hold_seconds
        ):
            self._dragging = True
            self._clear_pending_double_click()
            if self._relative_mode():
                self._drag_reference_pointer = self._pointer(frame)
                self._set_status(frame, "dragging", "pinch held beyond drag threshold")
                return [InteractionEvent("drag_start")]
            self._smoothed_drag_pointer = self._anchored_pointer(frame)
            self._set_status(frame, "dragging", "pinch held beyond drag threshold")
            return [InteractionEvent("drag_start", position=self._anchored_pointer(frame))]

        if self._dragging:
            self._set_status(frame, "dragging", "dragging")
            if self._relative_mode():
                dx, dy = self._relative_drag_delta(frame)
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    return []
                return [InteractionEvent("drag_move", dx=dx, dy=dy)]
            return [InteractionEvent("drag_move", position=self._anchored_drag_pointer(frame))]

        self._set_status(frame, "pinch_active", "pinch held")
        return []

    def _handle_pinch_released(self, frame: HandFrame, timestamp: float) -> list[InteractionEvent]:
        self._pinch_candidate_frames = 0
        self._pinch_candidate_started_at = None
        self._pinch_armed = True
        if not self._pinching:
            return []

        self._pinching = False
        self._pinch_started_at = None

        if self._dragging:
            self._dragging = False
            self._set_status(frame, "drag_end", "pinch released after drag")
            self._clear_pinch_anchor()
            return [InteractionEvent("drag_end")]

        click_count = 1
        if (
            self._last_click_at is not None
            and timestamp - self._last_click_at <= self.config.double_click_window_seconds
        ):
            click_count = 2
            self._last_click_at = None
        else:
            self._last_click_at = timestamp

        self._set_status(frame, "click", f"click_count={click_count}")
        if self._relative_mode():
            self._clear_pinch_anchor()
            return [InteractionEvent("click", click_count=click_count)]
        position = self._anchored_pointer(frame)
        self._clear_pinch_anchor()
        return [InteractionEvent("click", position=position, click_count=click_count)]

    def _handle_scroll(self, frame: HandFrame) -> list[InteractionEvent]:
        self._clear_pending_double_click()
        point = self._pointer(frame)
        if not self._scrolling:
            self._scrolling = True
            self._last_scroll_point = point
            self._set_status(frame, "scrolling", "two-finger scroll mode")
            return []

        if self._last_scroll_point is None:
            self._last_scroll_point = point
            return []

        dx = (point.x - self._last_scroll_point.x) * self.config.scroll_sensitivity
        dy = (self._last_scroll_point.y - point.y) * self.config.scroll_sensitivity
        self._last_scroll_point = point
        if abs(dx) < 1 and abs(dy) < 1:
            self._set_status(frame, "scrolling", "scroll delta below threshold")
            return []
        self._set_status(frame, "scrolling", "scrolling")
        return [InteractionEvent("scroll", dx=dx, dy=dy)]

    def _clear_scroll_state(self) -> None:
        self._scrolling = False
        self._last_scroll_point = None

    def _clear_pending_double_click(self) -> None:
        self._last_click_at = None

    def _handle_relative_move(self, frame: HandFrame) -> list[InteractionEvent]:
        if not self._is_move_control_pose(frame):
            self._reset_relative_reference()
            self._set_status(frame, "clutch", "index relaxed for hand repositioning")
            return []

        pointer = self._smooth_pointer(self._pointer(frame))
        self._last_hover_pointer = pointer
        if self._relative_reference_pointer is None or self._relative_warmup_remaining > 0:
            self._relative_reference_pointer = pointer
            self._comfort_center = pointer
            self._relative_warmup_remaining = max(self._relative_warmup_remaining - 1, 0)
            self._set_status(frame, "active_move", "relative pointer reference established")
            return []

        raw_dx = pointer.x - self._relative_reference_pointer.x
        raw_dy = pointer.y - self._relative_reference_pointer.y
        self._relative_reference_pointer = pointer

        dx, dy = self._apply_relative_gain(raw_dx, raw_dy)
        cruise_dx, cruise_dy = self._edge_cruise_delta(pointer)
        dx += cruise_dx
        dy += cruise_dy

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            self._set_status(frame, "active_move", "relative movement below threshold")
            return []

        state = "edge_cruise" if abs(cruise_dx) > 0 or abs(cruise_dy) > 0 else "active_move"
        reason = "comfort zone edge cruise" if state == "edge_cruise" else "relative pointer delta"
        self._set_status(frame, state, reason)
        return [InteractionEvent("move", dx=dx, dy=dy)]

    def _is_pinch_contact(self, frame: HandFrame) -> bool:
        thumb = frame.landmarks[4]
        index = frame.landmarks[8]
        distance = _distance(thumb, index)
        scale = self._pinch_scale(frame)
        scaled_distance = distance / scale
        if self._pinching:
            return (
                distance <= self.config.pinch_release_threshold
                and scaled_distance <= self.config.pinch_release_scale_threshold
            )
        if distance > self.config.pinch_threshold:
            return False
        if scaled_distance > self.config.pinch_scale_threshold:
            return False

        middle = frame.landmarks[12]
        index_middle_distance = _distance(index, middle)
        thumb_middle_distance = _distance(thumb, middle)
        isolated_index = index_middle_distance >= self.config.pinch_isolation_distance
        thumb_prefers_index = distance + 0.015 < thumb_middle_distance
        return isolated_index and thumb_prefers_index

    def _is_scroll_mode(self, frame: HandFrame) -> bool:
        if self._is_pinch_contact(frame):
            return False
        index_extended = frame.landmarks[8].y < frame.landmarks[6].y
        middle_extended = frame.landmarks[12].y < frame.landmarks[10].y
        ring_folded = frame.landmarks[16].y > frame.landmarks[14].y
        pinky_folded = frame.landmarks[20].y > frame.landmarks[18].y
        return index_extended and middle_extended and ring_folded and pinky_folded

    def _is_move_control_pose(self, frame: HandFrame) -> bool:
        return frame.landmarks[8].y < frame.landmarks[6].y

    def _is_open_palm(self, frame: HandFrame) -> bool:
        if self._is_pinch_contact(frame):
            return False
        fingers_extended = (
            frame.landmarks[8].y < frame.landmarks[6].y
            and frame.landmarks[12].y < frame.landmarks[10].y
            and frame.landmarks[16].y < frame.landmarks[14].y
            and frame.landmarks[20].y < frame.landmarks[18].y
        )
        thumb_away = _distance(frame.landmarks[4], frame.landmarks[0]) > 0.18
        return fingers_extended and thumb_away

    def _pointer(self, frame: HandFrame) -> Point:
        return frame.landmarks[8]

    def _pinch_scale(self, frame: HandFrame) -> float:
        index_length = _distance(frame.landmarks[5], frame.landmarks[8])
        middle_length = _distance(frame.landmarks[9], frame.landmarks[12])
        palm_width = _distance(frame.landmarks[5], frame.landmarks[17])
        palm_diagonal = _distance(frame.landmarks[0], frame.landmarks[9])
        return max(index_length, middle_length, palm_width * 0.5, palm_diagonal * 0.8, 1e-6)

    def _anchored_pointer(self, frame: HandFrame) -> Point:
        return self._pinch_anchor or self._pointer(frame)

    def _anchored_drag_pointer(self, frame: HandFrame) -> Point:
        if self._pinch_anchor is None or self._drag_reference_pointer is None:
            return self._smooth_drag_pointer(self._pointer(frame))
        current = self._pointer(frame)
        raw_position = Point(
            x=_clamp(self._pinch_anchor.x + current.x - self._drag_reference_pointer.x),
            y=_clamp(self._pinch_anchor.y + current.y - self._drag_reference_pointer.y),
        )
        return self._smooth_drag_pointer(raw_position)

    def _relative_drag_delta(self, frame: HandFrame) -> tuple[float, float]:
        pointer = self._smooth_drag_pointer(self._pointer(frame))
        if self._drag_reference_pointer is None:
            self._drag_reference_pointer = pointer
            return 0.0, 0.0
        raw_dx = pointer.x - self._drag_reference_pointer.x
        raw_dy = pointer.y - self._drag_reference_pointer.y
        self._drag_reference_pointer = pointer
        return self._apply_relative_gain(raw_dx, raw_dy)

    def _clear_pinch_anchor(self) -> None:
        self._pinch_anchor = None
        self._drag_reference_pointer = None
        self._smoothed_drag_pointer = None

    def _cancel_active_pinch(self) -> None:
        self._pinching = False
        self._pinch_started_at = None
        self._dragging = False
        self._pinch_candidate_frames = 0
        self._pinch_candidate_started_at = None
        self._pinch_armed = True
        self._clear_pinch_anchor()

    def _smooth_pointer(self, point: Point) -> Point:
        self._smoothed_pointer = _smooth_point(
            previous=self._smoothed_pointer,
            current=point,
            alpha=self.config.pointer_smoothing_alpha,
        )
        return self._smoothed_pointer

    def _smooth_drag_pointer(self, point: Point) -> Point:
        self._smoothed_drag_pointer = _smooth_point(
            previous=self._smoothed_drag_pointer,
            current=point,
            alpha=self.config.pointer_smoothing_alpha,
        )
        return self._smoothed_drag_pointer

    def _reset_smoothing(self) -> None:
        self._smoothed_pointer = None
        self._smoothed_drag_pointer = None

    def _relative_mode(self) -> bool:
        return self.config.movement_mode.lower() == "relative"

    def _apply_relative_gain(self, dx: float, dy: float) -> tuple[float, float]:
        motion = _distance(Point(0, 0), Point(dx, dy))
        threshold = max(self.config.relative_gain_motion_threshold, 1e-6)
        ratio = min(motion / threshold, 1.0)
        gain = self.config.relative_min_gain + (
            self.config.relative_max_gain - self.config.relative_min_gain
        ) * ratio
        multiplier = self.config.relative_sensitivity * gain
        return (
            _clamp_range(dx * multiplier, -self.config.relative_max_delta, self.config.relative_max_delta),
            _clamp_range(dy * multiplier, -self.config.relative_max_delta, self.config.relative_max_delta),
        )

    def _edge_cruise_delta(self, pointer: Point) -> tuple[float, float]:
        if self._comfort_center is None or self.config.edge_cruise_speed <= 0:
            return 0.0, 0.0
        dx = self._axis_cruise_delta(
            value=pointer.x,
            center=self._comfort_center.x,
            size=self.config.comfort_zone_width,
        )
        dy = self._axis_cruise_delta(
            value=pointer.y,
            center=self._comfort_center.y,
            size=self.config.comfort_zone_height,
        )
        return dx, dy

    def _axis_cruise_delta(self, *, value: float, center: float, size: float) -> float:
        half_size = max(size / 2, 1e-6)
        threshold = half_size * (1 - _clamp(self.config.edge_cruise_margin))
        offset = value - center
        if abs(offset) < threshold:
            return 0.0
        return self.config.edge_cruise_speed * 0.5 * (1 if offset > 0 else -1)

    def _clear_relative_state(self) -> None:
        self._comfort_center = None
        self._reset_relative_reference()

    def _reset_relative_reference(self) -> None:
        self._relative_reference_pointer = None
        self._relative_warmup_remaining = self.config.relative_warmup_frames

    def _is_target_hand(self, frame: HandFrame) -> bool:
        if self.config.target_handedness.lower() == "any":
            return True
        return frame.handedness.lower() == self.config.target_handedness.lower()

    def _set_status(self, frame: HandFrame, state: str, reason: str) -> None:
        self.status = GestureStatus(
            state=state,
            handedness=frame.handedness,
            confidence=frame.confidence,
            pinch_distance=_distance(frame.landmarks[4], frame.landmarks[8]),
            pinch_scaled_distance=_distance(frame.landmarks[4], frame.landmarks[8])
            / self._pinch_scale(frame),
            reason=reason,
        )


def _distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _clamp_range(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _smooth_point(*, previous: Point | None, current: Point, alpha: float) -> Point:
    alpha = _clamp(alpha)
    if previous is None or alpha >= 1:
        return current
    if alpha <= 0:
        return previous
    return Point(
        x=previous.x + (current.x - previous.x) * alpha,
        y=previous.y + (current.y - previous.y) * alpha,
    )
