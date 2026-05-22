from types import SimpleNamespace

from new_interaction.camera import (
    CameraHandTracker,
    HAND_LANDMARKER_MODEL_URL,
    default_model_path,
    hand_frame_from_mediapipe,
    normalize_handedness,
)


def test_hand_frame_from_mediapipe_converts_21_landmarks():
    landmarks = [SimpleNamespace(x=i / 100, y=(100 - i) / 100) for i in range(21)]

    frame = hand_frame_from_mediapipe(landmarks, handedness="Right", confidence=0.88)

    assert frame.handedness == "Right"
    assert frame.confidence == 0.88
    assert frame.landmarks[0].x == 0
    assert frame.landmarks[8].x == 0.08
    assert frame.landmarks[20].y == 0.8


def test_default_model_path_uses_cache_directory():
    path = default_model_path()

    assert path.name == "hand_landmarker.task"
    assert "new_interaction" in path.parts
    assert HAND_LANDMARKER_MODEL_URL.endswith("/hand_landmarker.task")


def test_normalize_handedness_swaps_label_for_mirrored_input():
    assert normalize_handedness("Left", mirror=True) == "Right"
    assert normalize_handedness("Right", mirror=True) == "Left"
    assert normalize_handedness("Right", mirror=False) == "Right"


def make_landmarks(offset: float):
    return [SimpleNamespace(x=offset + i / 100, y=(100 - i) / 100) for i in range(21)]


def make_handedness(name: str, score: float):
    return [SimpleNamespace(category_name=name, score=score)]


def test_extract_hand_prefers_target_handedness_when_two_hands_detected():
    tracker = CameraHandTracker.__new__(CameraHandTracker)
    tracker.mirror = False
    tracker.target_handedness = "Right"
    result = SimpleNamespace(
        hand_landmarks=[make_landmarks(0.10), make_landmarks(0.40)],
        handedness=[make_handedness("Left", 0.91), make_handedness("Right", 0.93)],
    )

    frame = tracker._extract_hand(result)

    assert frame is not None
    assert frame.handedness == "Right"
    assert frame.confidence == 0.93
    assert frame.landmarks[0].x == 0.40


def test_extract_hand_can_select_left_target_handedness():
    tracker = CameraHandTracker.__new__(CameraHandTracker)
    tracker.mirror = False
    tracker.target_handedness = "Left"
    result = SimpleNamespace(
        hand_landmarks=[make_landmarks(0.10), make_landmarks(0.40)],
        handedness=[make_handedness("Right", 0.93), make_handedness("Left", 0.91)],
    )

    frame = tracker._extract_hand(result)

    assert frame is not None
    assert frame.handedness == "Left"
    assert frame.confidence == 0.91
    assert frame.landmarks[0].x == 0.40
