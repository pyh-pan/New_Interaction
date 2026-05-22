from new_interaction.gestures import InteractionEvent, Point
from new_interaction.input_controller import (
    DryRunInputController,
    PyAutoGUIInputController,
    map_point_to_screen,
)


def test_map_point_to_screen_clamps_normalized_coordinates():
    assert map_point_to_screen(Point(-0.5, 1.5), width=1000, height=500) == (0, 499)
    assert map_point_to_screen(Point(1, 1), width=1000, height=500) == (999, 499)
    assert map_point_to_screen(Point(1, 1), width=1, height=1) == (0, 0)


def test_dry_run_controller_records_mouse_events_without_side_effects():
    controller = DryRunInputController(width=1000, height=500)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    controller.handle(InteractionEvent("click", position=Point(0.25, 0.50), click_count=2))
    controller.handle(InteractionEvent("scroll", dx=10, dy=-20))
    controller.handle(InteractionEvent("pause_changed", paused=True))

    assert controller.events == [
        "move 250 250",
        "click 250 250 count=2",
        "scroll dx=10.0 dy=-20.0",
        "pause paused=True",
    ]


def test_dry_run_controller_records_relative_mouse_events_without_side_effects():
    controller = DryRunInputController(width=1000, height=500)

    controller.handle(InteractionEvent("move", dx=0.05, dy=-0.02))
    controller.handle(InteractionEvent("click", click_count=1))
    controller.handle(InteractionEvent("drag_start"))
    controller.handle(InteractionEvent("drag_move", dx=0.04, dy=0.02))
    controller.handle(InteractionEvent("drag_end"))

    assert controller.events == [
        "move-rel dx=50 dy=-10",
        "click current count=1",
        "drag-start current",
        "drag-move-rel dx=40 dy=10",
        "drag-end",
    ]


class FakePyAutoGUI:
    FAILSAFE = False
    PAUSE = 0

    def __init__(self):
        self.calls = []
        self.cursor = (0, 0)

    def size(self):
        return (1000, 500)

    def moveTo(self, x, y, duration=0):
        self.calls.append(("moveTo", x, y, duration))
        self.cursor = (x, y)

    def moveRel(self, xOffset=0, yOffset=0, duration=0):
        self.calls.append(("moveRel", xOffset, yOffset, duration))
        self.cursor = (self.cursor[0] + xOffset, self.cursor[1] + yOffset)

    def dragTo(self, x, y, duration=0, button="primary", mouseDownUp=True):
        if button not in {"left", "middle", "right"}:
            raise AssertionError("button argument not in ('left', 'middle', 'right')")
        self.calls.append(("dragTo", x, y, duration, button, mouseDownUp))
        self.cursor = (x, y)

    def dragRel(self, xOffset=0, yOffset=0, duration=0, button="primary", mouseDownUp=True):
        if button not in {"left", "middle", "right"}:
            raise AssertionError("button argument not in ('left', 'middle', 'right')")
        self.calls.append(("dragRel", xOffset, yOffset, duration, button, mouseDownUp))
        self.cursor = (self.cursor[0] + xOffset, self.cursor[1] + yOffset)

    def position(self):
        return self.cursor

    def click(self, clicks=1):
        self.calls.append(("click", clicks))

    def mouseDown(self):
        self.calls.append(("mouseDown",))

    def mouseUp(self):
        self.calls.append(("mouseUp",))

    def hscroll(self, amount):
        self.calls.append(("hscroll", amount))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))


def test_pyautogui_controller_honors_click_count():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("click", position=Point(0.25, 0.50), click_count=2))

    assert fake.calls == [("moveTo", 250, 250, 0), ("click", 2)]


def test_pyautogui_controller_handles_relative_move_delta():
    fake = FakePyAutoGUI()
    fake.cursor = (100, 100)
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", dx=0.05, dy=-0.02))

    assert fake.calls == [("moveRel", 50, -10, 0)]
    assert fake.cursor == (150, 90)


def test_pyautogui_controller_clicks_current_pointer_without_absolute_position():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("click", click_count=1))

    assert fake.calls == [("click", 1)]


def test_pyautogui_controller_uses_drag_events_while_mouse_is_down():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("drag_start", position=Point(0.25, 0.50)))
    controller.handle(InteractionEvent("drag_move", position=Point(0.30, 0.55)))
    controller.handle(InteractionEvent("drag_end", position=Point(0.35, 0.60)))

    assert fake.calls == [
        ("moveTo", 250, 250, 0),
        ("mouseDown",),
        ("dragTo", 300, 274, 0, "left", False),
        ("dragTo", 350, 299, 0, "left", False),
        ("mouseUp",),
    ]


def test_pyautogui_controller_uses_relative_drag_events_while_mouse_is_down():
    fake = FakePyAutoGUI()
    fake.cursor = (100, 100)
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("drag_start"))
    controller.handle(InteractionEvent("drag_move", dx=0.04, dy=0.02))
    controller.handle(InteractionEvent("drag_end"))

    assert fake.calls == [
        ("mouseDown",),
        ("dragRel", 40, 10, 0, "left", False),
        ("mouseUp",),
    ]
    assert fake.cursor == (140, 110)


def test_pyautogui_controller_suspends_when_user_moves_real_mouse():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    fake.cursor = (800, 400)
    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))

    assert fake.calls == [("moveTo", 250, 250, 0)]


def test_pyautogui_controller_suppresses_click_during_user_takeover():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    fake.cursor = (800, 400)
    controller.handle(InteractionEvent("click", position=Point(0.25, 0.50), click_count=1))

    assert fake.calls == [("moveTo", 250, 250, 0)]


def test_pyautogui_controller_suppresses_scroll_during_user_takeover():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    fake.cursor = (800, 400)
    controller.handle(InteractionEvent("scroll", dx=10, dy=-20))

    assert fake.calls == [("moveTo", 250, 250, 0)]


def test_pyautogui_controller_rearms_after_tracking_lost():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    fake.cursor = (800, 400)
    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    controller.handle(InteractionEvent("move", position=Point(0.40, 0.40)))
    controller.handle(InteractionEvent("tracking_lost"))
    controller.handle(InteractionEvent("move", position=Point(0.10, 0.20)))

    assert fake.calls == [("moveTo", 250, 250, 0), ("moveTo", 100, 100, 0)]


def test_pyautogui_controller_rearms_after_pause_changed():
    fake = FakePyAutoGUI()
    controller = PyAutoGUIInputController(pyautogui_module=fake)

    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    fake.cursor = (800, 400)
    controller.handle(InteractionEvent("move", position=Point(0.25, 0.50)))
    controller.handle(InteractionEvent("move", position=Point(0.40, 0.40)))
    controller.handle(InteractionEvent("pause_changed", paused=True))
    controller.handle(InteractionEvent("move", position=Point(0.10, 0.20)))

    assert fake.calls == [("moveTo", 250, 250, 0), ("moveTo", 100, 100, 0)]
