from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from urllib.request import urlretrieve

from new_interaction.gestures import HandFrame, Point


class DependencyError(RuntimeError):
    pass


HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


@dataclass(frozen=True)
class CameraFrame:
    image: object
    hand: HandFrame | None


def default_model_path() -> Path:
    return Path.home() / ".cache" / "new_interaction" / "hand_landmarker.task"


def ensure_model(path: Path | None = None) -> Path:
    model_path = path or default_model_path()
    if model_path.exists():
        return model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MediaPipe hand model to {model_path}")
    urlretrieve(HAND_LANDMARKER_MODEL_URL, model_path)
    return model_path


def normalize_handedness(handedness: str, *, mirror: bool) -> str:
    if not mirror:
        return handedness
    if handedness == "Left":
        return "Right"
    if handedness == "Right":
        return "Left"
    return handedness


def hand_frame_from_mediapipe(
    landmarks: object,
    *,
    handedness: str,
    confidence: float,
    mirror_x: bool = False,
) -> HandFrame:
    points = {}
    for index, landmark in enumerate(landmarks):
        x = 1.0 - float(landmark.x) if mirror_x else float(landmark.x)
        points[index] = Point(x=x, y=float(landmark.y))
    return HandFrame(landmarks=points, handedness=handedness, confidence=confidence)


class CameraHandTracker:
    def __init__(
        self,
        *,
        camera_index: int = 0,
        model_path: Path | None = None,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
        mirror: bool = True,
        max_fps: float = 30.0,
        target_handedness: str = "Right",
    ) -> None:
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise DependencyError(
                "Missing camera dependencies. Install them with "
                "`.venv/bin/python -m pip install -e .`."
            ) from exc

        self._cv2 = cv2
        self._mp = mp
        self._vision = vision
        self.camera_index = camera_index
        self.mirror = mirror
        self.max_fps = max_fps
        self.target_handedness = target_handedness
        self._capture = None
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(ensure_model(model_path))),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def __enter__(self) -> CameraHandTracker:
        self._capture = self._cv2.VideoCapture(self.camera_index)
        if not self._capture.isOpened():
            raise RuntimeError(
                f"Unable to open camera index {self.camera_index}. "
                "Check macOS Camera permission and whether another app is using the camera."
            )
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._capture is not None:
            self._capture.release()
        self._landmarker.close()
        self._cv2.destroyAllWindows()

    def frames(self) -> Iterator[CameraFrame]:
        if self._capture is None:
            raise RuntimeError("CameraHandTracker must be used as a context manager.")

        min_interval = 1.0 / self.max_fps if self.max_fps > 0 else 0.0
        last_frame_at = 0.0
        while True:
            now = monotonic()
            elapsed = now - last_frame_at
            if elapsed < min_interval:
                sleep(min_interval - elapsed)
            last_frame_at = monotonic()

            ok, image = self._capture.read()
            if not ok:
                raise RuntimeError("Camera frame capture failed.")

            if self.mirror:
                image = self._cv2.flip(image, 1)

            rgb = self._cv2.cvtColor(image, self._cv2.COLOR_BGR2RGB)
            mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(mp_image)
            yield CameraFrame(image=image, hand=self._extract_hand(result))

    def draw_debug(self, image: object, hand: HandFrame | None) -> object:
        if hand is None:
            return image
        height, width = image.shape[:2]
        for point in hand.landmarks.values():
            self._cv2.circle(
                image,
                (round(point.x * width), round(point.y * height)),
                3,
                (44, 176, 255),
                -1,
            )
        return image

    def _extract_hand(self, result: object) -> HandFrame | None:
        if not result.hand_landmarks:
            return None
        candidates = [
            self._hand_frame_for_index(result, index)
            for index in range(len(result.hand_landmarks))
        ]
        if self.target_handedness.lower() == "any":
            return candidates[0]
        for candidate in candidates:
            if candidate.handedness.lower() == self.target_handedness.lower():
                return candidate
        return candidates[0]

    def _hand_frame_for_index(self, result: object, index: int) -> HandFrame:
        handedness = "Unknown"
        confidence = 1.0
        if result.handedness and index < len(result.handedness):
            category = result.handedness[index][0]
            handedness = category.category_name
            confidence = category.score
        handedness = normalize_handedness(handedness, mirror=self.mirror)
        return hand_frame_from_mediapipe(
            result.hand_landmarks[index],
            handedness=handedness,
            confidence=confidence,
            mirror_x=False,
        )
