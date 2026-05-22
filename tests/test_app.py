from types import SimpleNamespace

import new_interaction.app as app
from new_interaction.app import parse_args


def test_parse_args_defaults_to_dry_run_mode():
    args = parse_args([])

    assert args.control is False
    assert args.camera_index == 0
    assert args.show_preview is False
    assert args.max_frames is None
    assert args.target_hand == "Right"
    assert args.debug_state is False
    assert args.pinch_scale_threshold == 0.30
    assert args.pinch_release_scale_threshold == 0.45
    assert args.pointer_smoothing_alpha == 0.35
    assert args.movement_mode == "relative"
    assert args.relative_sensitivity == 1.20
    assert args.relative_max_gain == 2.40
    assert args.relative_max_delta == 0.08
    assert args.edge_cruise_speed == 0.006
    assert args.relative_warmup_frames == 3


def test_parse_args_accepts_control_and_preview():
    args = parse_args(
        [
            "--control",
            "--show-preview",
            "--camera-index",
            "2",
            "--max-frames",
            "5",
            "--target-hand",
            "Any",
            "--pinch-scale-threshold",
            "0.24",
            "--pinch-release-scale-threshold",
            "0.60",
            "--pointer-smoothing-alpha",
            "0.20",
            "--movement-mode",
            "absolute",
            "--relative-sensitivity",
            "1.5",
            "--relative-min-gain",
            "0.7",
            "--relative-max-gain",
            "3.5",
            "--relative-gain-motion-threshold",
            "0.06",
            "--relative-max-delta",
            "0.07",
            "--relative-warmup-frames",
            "4",
            "--comfort-zone-width",
            "0.42",
            "--comfort-zone-height",
            "0.32",
            "--edge-cruise-margin",
            "0.20",
            "--edge-cruise-speed",
            "0.02",
            "--debug-state",
        ]
    )

    assert args.control is True
    assert args.show_preview is True
    assert args.camera_index == 2
    assert args.max_frames == 5
    assert args.target_hand == "Any"
    assert args.pinch_scale_threshold == 0.24
    assert args.pinch_release_scale_threshold == 0.60
    assert args.pointer_smoothing_alpha == 0.20
    assert args.movement_mode == "absolute"
    assert args.relative_sensitivity == 1.5
    assert args.relative_min_gain == 0.7
    assert args.relative_max_gain == 3.5
    assert args.relative_gain_motion_threshold == 0.06
    assert args.relative_max_delta == 0.07
    assert args.relative_warmup_frames == 4
    assert args.comfort_zone_width == 0.42
    assert args.comfort_zone_height == 0.32
    assert args.edge_cruise_margin == 0.20
    assert args.edge_cruise_speed == 0.02
    assert args.debug_state is True


def test_main_passes_target_hand_to_camera_tracker(monkeypatch, capsys):
    captured = {}

    class FakeTracker:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self._cv2 = SimpleNamespace()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def frames(self):
            yield SimpleNamespace(image=None, hand=None)

    monkeypatch.setattr(app, "CameraHandTracker", FakeTracker)

    result = app.main(["--target-hand", "Left", "--max-frames", "1"])

    assert result == 0
    assert captured["target_handedness"] == "Left"
