from __future__ import annotations

import argparse
from time import monotonic

from new_interaction.camera import CameraHandTracker, DependencyError
from new_interaction.gestures import GestureConfig, GestureStateMachine
from new_interaction.input_controller import DryRunInputController, PyAutoGUIInputController


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Engineering prototype for camera-based gesture mouse control."
    )
    parser.add_argument("--camera-index", type=int, default=0, help="OpenCV camera index.")
    parser.add_argument(
        "--control",
        action="store_true",
        help="Inject real mouse events with PyAutoGUI. Default is dry-run logging.",
    )
    parser.add_argument(
        "--show-preview",
        action="store_true",
        help="Show a local OpenCV preview with detected hand landmarks.",
    )
    parser.add_argument("--max-fps", type=float, default=30.0, help="Maximum camera loop FPS.")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop automatically after this many camera frames. Useful for smoke tests.",
    )
    parser.add_argument(
        "--pinch-threshold",
        type=float,
        default=GestureConfig.pinch_threshold,
        help="Normalized thumb-index distance below which pinch is active.",
    )
    parser.add_argument(
        "--pinch-release-threshold",
        type=float,
        default=GestureConfig.pinch_release_threshold,
        help="Normalized thumb-index distance above which an active pinch is released.",
    )
    parser.add_argument(
        "--pinch-scale-threshold",
        type=float,
        default=GestureConfig.pinch_scale_threshold,
        help="Thumb-index distance divided by hand scale required to enter strict pinch.",
    )
    parser.add_argument(
        "--pinch-release-scale-threshold",
        type=float,
        default=GestureConfig.pinch_release_scale_threshold,
        help="Scaled thumb-index distance above which an active pinch is released.",
    )
    parser.add_argument(
        "--pinch-confirm-frames",
        type=int,
        default=GestureConfig.pinch_confirm_frames,
        help="Consecutive strict-pinch frames required before pinch becomes active.",
    )
    parser.add_argument(
        "--pinch-isolation-distance",
        type=float,
        default=GestureConfig.pinch_isolation_distance,
        help="Minimum index-middle fingertip distance for a strict pinch.",
    )
    parser.add_argument(
        "--target-hand",
        choices=["Right", "Left", "Any"],
        default=GestureConfig.target_handedness,
        help="Only this physical hand can control the pointer.",
    )
    parser.add_argument(
        "--debug-state",
        action="store_true",
        help="Print state changes explaining why gestures are accepted or ignored.",
    )
    parser.add_argument(
        "--drag-hold",
        type=float,
        default=GestureConfig.drag_hold_seconds,
        help="Seconds to hold pinch before drag starts.",
    )
    parser.add_argument(
        "--double-click-window",
        type=float,
        default=GestureConfig.double_click_window_seconds,
        help="Seconds between short pinches to mark the second as double-click.",
    )
    parser.add_argument(
        "--pause-hold",
        type=float,
        default=GestureConfig.pause_hold_seconds,
        help="Seconds to hold open palm before toggling pause.",
    )
    parser.add_argument(
        "--scroll-sensitivity",
        type=float,
        default=GestureConfig.scroll_sensitivity,
        help="Scroll delta multiplier for two-finger scroll mode.",
    )
    parser.add_argument(
        "--pointer-smoothing-alpha",
        type=float,
        default=GestureConfig.pointer_smoothing_alpha,
        help="Pointer smoothing alpha. Lower is steadier; higher is more responsive.",
    )
    parser.add_argument(
        "--movement-mode",
        choices=["relative", "absolute"],
        default=GestureConfig.movement_mode,
        help="Pointer mapping mode. Relative is the comfort-zone default; absolute is for debugging.",
    )
    parser.add_argument(
        "--relative-sensitivity",
        type=float,
        default=GestureConfig.relative_sensitivity,
        help="Base multiplier for relative hand movement.",
    )
    parser.add_argument(
        "--relative-min-gain",
        type=float,
        default=GestureConfig.relative_min_gain,
        help="Gain applied to slow relative movement for precise control.",
    )
    parser.add_argument(
        "--relative-max-gain",
        type=float,
        default=GestureConfig.relative_max_gain,
        help="Gain applied to fast relative movement for large screens.",
    )
    parser.add_argument(
        "--relative-gain-motion-threshold",
        type=float,
        default=GestureConfig.relative_gain_motion_threshold,
        help="Normalized per-frame motion that reaches maximum relative gain.",
    )
    parser.add_argument(
        "--relative-max-delta",
        type=float,
        default=GestureConfig.relative_max_delta,
        help="Maximum normalized pointer delta emitted from one relative frame.",
    )
    parser.add_argument(
        "--relative-warmup-frames",
        type=int,
        default=GestureConfig.relative_warmup_frames,
        help="Frames used to stabilize hand tracking before relative movement starts.",
    )
    parser.add_argument(
        "--comfort-zone-width",
        type=float,
        default=GestureConfig.comfort_zone_width,
        help="Normalized width of the automatic comfort zone.",
    )
    parser.add_argument(
        "--comfort-zone-height",
        type=float,
        default=GestureConfig.comfort_zone_height,
        help="Normalized height of the automatic comfort zone.",
    )
    parser.add_argument(
        "--edge-cruise-margin",
        type=float,
        default=GestureConfig.edge_cruise_margin,
        help="Comfort-zone edge band used to start edge cruise.",
    )
    parser.add_argument(
        "--edge-cruise-speed",
        type=float,
        default=GestureConfig.edge_cruise_speed,
        help="Normalized pointer delta added each frame while holding the comfort-zone edge.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = GestureConfig(
        pinch_threshold=args.pinch_threshold,
        pinch_release_threshold=args.pinch_release_threshold,
        pinch_scale_threshold=args.pinch_scale_threshold,
        pinch_release_scale_threshold=args.pinch_release_scale_threshold,
        pinch_confirm_frames=args.pinch_confirm_frames,
        pinch_isolation_distance=args.pinch_isolation_distance,
        drag_hold_seconds=args.drag_hold,
        double_click_window_seconds=args.double_click_window,
        pause_hold_seconds=args.pause_hold,
        scroll_sensitivity=args.scroll_sensitivity,
        pointer_smoothing_alpha=args.pointer_smoothing_alpha,
        movement_mode=args.movement_mode,
        relative_sensitivity=args.relative_sensitivity,
        relative_min_gain=args.relative_min_gain,
        relative_max_gain=args.relative_max_gain,
        relative_gain_motion_threshold=args.relative_gain_motion_threshold,
        relative_max_delta=args.relative_max_delta,
        relative_warmup_frames=args.relative_warmup_frames,
        comfort_zone_width=args.comfort_zone_width,
        comfort_zone_height=args.comfort_zone_height,
        edge_cruise_margin=args.edge_cruise_margin,
        edge_cruise_speed=args.edge_cruise_speed,
        target_handedness=args.target_hand,
    )
    gestures = GestureStateMachine(config)
    controller = PyAutoGUIInputController() if args.control else DryRunInputController()

    if not args.control:
        print("Running in dry-run mode. Add --control to inject real mouse events.")
    else:
        print("Running in control mode. Move mouse to a screen corner to trigger PyAutoGUI fail-safe.")

    try:
        with CameraHandTracker(
            camera_index=args.camera_index,
            max_fps=args.max_fps,
            target_handedness=args.target_hand,
        ) as tracker:
            print("Camera opened. Press q in the preview window or Ctrl+C in terminal to stop.")
            frame_count = 0
            last_status_text = ""
            for camera_frame in tracker.frames():
                frame_count += 1
                events = gestures.update(camera_frame.hand, timestamp=monotonic())
                if args.debug_state:
                    status = gestures.status
                    pinch_distance = (
                        f"{status.pinch_distance:.3f}" if status.pinch_distance is not None else "-"
                    )
                    pinch_scaled_distance = (
                        f"{status.pinch_scaled_distance:.2f}"
                        if status.pinch_scaled_distance is not None
                        else "-"
                    )
                    status_text = (
                        f"state={status.state} hand={status.handedness} "
                        f"conf={status.confidence:.2f} "
                        f"pinch={pinch_distance} pinch_scale={pinch_scaled_distance} "
                        f"reason={status.reason}"
                    )
                    if status_text != last_status_text:
                        print(status_text)
                        last_status_text = status_text
                for event in events:
                    controller.handle(event)

                if args.show_preview:
                    image = tracker.draw_debug(camera_frame.image, camera_frame.hand)
                    tracker._cv2.imshow("New Interaction - hand tracking", image)
                    if tracker._cv2.waitKey(1) & 0xFF == ord("q"):
                        return 0
                if args.max_frames is not None and frame_count >= args.max_frames:
                    return 0
    except KeyboardInterrupt:
        return 0
    except DependencyError as exc:
        print(f"Dependency error: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"Runtime error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
