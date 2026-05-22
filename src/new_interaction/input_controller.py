from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Protocol

from new_interaction.gestures import InteractionEvent, Point


class InputController(Protocol):
    def handle(self, event: InteractionEvent) -> None:
        ...


def map_point_to_screen(point: Point, *, width: int, height: int) -> tuple[int, int]:
    x = min(max(point.x, 0.0), 1.0)
    y = min(max(point.y, 0.0), 1.0)
    max_x = max(width - 1, 0)
    max_y = max(height - 1, 0)
    return round(x * max_x), round(y * max_y)


@dataclass
class DryRunInputController:
    width: int = 1440
    height: int = 900
    events: list[str] = field(default_factory=list)

    def handle(self, event: InteractionEvent) -> None:
        if event.kind in {"move", "drag_move"} and event.position is None:
            x_offset = round(event.dx * self.width)
            y_offset = round(event.dy * self.height)
            message = f"{event.kind.replace('_', '-')}-rel dx={x_offset} dy={y_offset}"
        elif event.kind in {"drag_start", "click"} and event.position is None:
            if event.kind == "click":
                message = f"click current count={event.click_count}"
            else:
                message = "drag-start current"
        elif event.kind == "drag_end" and event.position is None:
            message = "drag-end"
        elif event.kind in {"move", "drag_start", "drag_move", "drag_end", "click"}:
            position = event.position or Point(0, 0)
            x, y = map_point_to_screen(position, width=self.width, height=self.height)
            if event.kind == "click":
                message = f"click {x} {y} count={event.click_count}"
            else:
                message = f"{event.kind.replace('_', '-')} {x} {y}"
        elif event.kind == "scroll":
            message = f"scroll dx={event.dx:.1f} dy={event.dy:.1f}"
        elif event.kind == "pause_changed":
            message = f"pause paused={event.paused}"
        else:
            message = event.kind
        self.events.append(message)
        print(message)


class PyAutoGUIInputController:
    def __init__(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        pyautogui_module=None,
        takeover_threshold_px: float = 32.0,
    ) -> None:
        if pyautogui_module is None:
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError(
                    "PyAutoGUI is not installed. Install dependencies with "
                    "`.venv/bin/python -m pip install -e .`."
                ) from exc
            pyautogui_module = pyautogui

        self._pyautogui = pyautogui_module
        self.width, self.height = (
            (width, height) if width and height else pyautogui_module.size()
        )
        self._dragging = False
        self._last_injected_position: tuple[int, int] | None = None
        self._takeover_threshold_px = takeover_threshold_px
        self._suspended = False
        pyautogui_module.FAILSAFE = True
        pyautogui_module.PAUSE = 0

    def handle(self, event: InteractionEvent) -> None:
        if event.kind == "move" and event.position:
            self._move(event.position)
        elif event.kind == "move":
            self._move_relative(event.dx, event.dy)
        elif event.kind == "click":
            if event.position and self._move(event.position):
                self._pyautogui.click(clicks=max(event.click_count, 1))
            elif event.position is None and not self._input_suppressed():
                self._pyautogui.click(clicks=max(event.click_count, 1))
        elif event.kind == "drag_start":
            if event.position and self._move(event.position):
                self._pyautogui.mouseDown()
                self._dragging = True
            elif event.position is None and not self._input_suppressed():
                self._pyautogui.mouseDown()
                self._dragging = True
        elif event.kind == "drag_move" and event.position:
            if not self._drag_to(event.position) and self._dragging:
                self._pyautogui.mouseUp()
                self._dragging = False
        elif event.kind == "drag_move":
            if not self._drag_relative(event.dx, event.dy) and self._dragging:
                self._pyautogui.mouseUp()
                self._dragging = False
        elif event.kind == "drag_end":
            if event.position and not self._drag_to(event.position) and self._dragging:
                self._pyautogui.mouseUp()
                self._dragging = False
            if self._dragging:
                self._pyautogui.mouseUp()
            self._dragging = False
        elif event.kind == "scroll":
            if not self._input_suppressed():
                self._pyautogui.hscroll(round(event.dx))
                self._pyautogui.scroll(round(event.dy))
        elif event.kind == "tracking_lost":
            if self._dragging:
                self._pyautogui.mouseUp()
                self._dragging = False
            self._rearm()
        elif event.kind == "pause_changed":
            self._rearm()

    def _move(self, point: Point) -> bool:
        x, y = map_point_to_screen(point, width=self.width, height=self.height)
        if self._input_suppressed():
            return False
        self._pyautogui.moveTo(x, y, duration=0)
        self._last_injected_position = (x, y)
        return True

    def _move_relative(self, dx: float, dy: float) -> bool:
        x_offset = round(dx * self.width)
        y_offset = round(dy * self.height)
        if x_offset == 0 and y_offset == 0:
            return True
        if self._input_suppressed():
            return False
        if hasattr(self._pyautogui, "moveRel"):
            self._pyautogui.moveRel(x_offset, y_offset, duration=0)
        else:
            current_x, current_y = self._current_position()
            self._pyautogui.moveTo(current_x + x_offset, current_y + y_offset, duration=0)
        self._last_injected_position = self._current_position()
        return True

    def _drag_to(self, point: Point) -> bool:
        x, y = map_point_to_screen(point, width=self.width, height=self.height)
        if self._input_suppressed():
            return False
        if hasattr(self._pyautogui, "dragTo"):
            self._pyautogui.dragTo(
                x,
                y,
                duration=0,
                button="left",
                mouseDownUp=False,
            )
        else:
            self._pyautogui.moveTo(x, y, duration=0)
        self._last_injected_position = (x, y)
        return True

    def _drag_relative(self, dx: float, dy: float) -> bool:
        x_offset = round(dx * self.width)
        y_offset = round(dy * self.height)
        if x_offset == 0 and y_offset == 0:
            return True
        if self._input_suppressed():
            return False
        if hasattr(self._pyautogui, "dragRel"):
            self._pyautogui.dragRel(
                x_offset,
                y_offset,
                duration=0,
                button="left",
                mouseDownUp=False,
            )
        elif hasattr(self._pyautogui, "dragTo"):
            current_x, current_y = self._current_position()
            self._pyautogui.dragTo(
                current_x + x_offset,
                current_y + y_offset,
                duration=0,
                button="left",
                mouseDownUp=False,
            )
        else:
            current_x, current_y = self._current_position()
            self._pyautogui.moveTo(current_x + x_offset, current_y + y_offset, duration=0)
        self._last_injected_position = self._current_position()
        return True

    def _input_suppressed(self) -> bool:
        return self._suspended or self._user_took_over()

    def _user_took_over(self) -> bool:
        if self._last_injected_position is None:
            return False
        current = self._current_position()
        distance = hypot(
            current[0] - self._last_injected_position[0],
            current[1] - self._last_injected_position[1],
        )
        if distance <= self._takeover_threshold_px:
            return False
        self._suspended = True
        return True

    def _rearm(self) -> None:
        self._suspended = False
        self._last_injected_position = None

    def _current_position(self) -> tuple[int, int]:
        position = self._pyautogui.position()
        if hasattr(position, "x") and hasattr(position, "y"):
            return (round(position.x), round(position.y))
        return (round(position[0]), round(position[1]))
