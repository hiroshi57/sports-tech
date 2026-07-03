"""MediaPipe による姿勢推定（骨格抽出）。

動画から各フレームの 33 個のランドマーク（関節点）時系列を抽出する。

依存 (mediapipe / opencv) は重いネイティブライブラリのため遅延 import する。
未インストール環境やテストでは PoseEstimationError を送出し、
呼び出し側（analysis_engine）がスタブにフォールバックする。

参考: MediaPipe Pose は 33 ランドマークを返す
https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field

from app.core import s3 as s3_client

logger = logging.getLogger(__name__)

# MediaPipe Pose のランドマーク総数
NUM_LANDMARKS = 33

# 主要ランドマークのインデックス（MediaPipe 定義）
LM_LEFT_SHOULDER = 11
LM_RIGHT_SHOULDER = 12
LM_LEFT_HIP = 23
LM_RIGHT_HIP = 24
LM_LEFT_ANKLE = 27
LM_RIGHT_ANKLE = 28
LM_LEFT_KNEE = 25
LM_RIGHT_KNEE = 26


class PoseEstimationError(RuntimeError):
    """mediapipe / opencv が利用できない場合に送出する。"""


@dataclass(frozen=True)
class Landmark:
    """正規化済みランドマーク座標（0〜1）。"""

    x: float
    y: float
    z: float
    visibility: float


@dataclass(frozen=True)
class PoseFrame:
    """1 フレーム分の全ランドマーク。"""

    landmarks: list[Landmark]


@dataclass(frozen=True)
class PoseSequence:
    """動画全体のポーズ時系列。"""

    frames: list[PoseFrame]
    fps: float
    width: int = 0
    height: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def duration_sec(self) -> float:
        if self.fps <= 0:
            return 0.0
        return len(self.frames) / self.fps


def _download_to_temp(s3_key: str) -> str:
    """S3 から動画を一時ファイルにダウンロードし、そのパスを返す。"""
    client = s3_client._get_s3_client()
    suffix = os.path.splitext(s3_key)[1] or ".mp4"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    client.download_file(s3_client.settings.S3_BUCKET_NAME, s3_key, path)
    return path


def extract_pose_from_file(
    video_path: str,
    sample_every_n_frames: int = 2,
    min_detection_confidence: float = 0.5,
) -> PoseSequence:
    """
    ローカル動画ファイルからポーズ時系列を抽出する。

    Args:
        video_path: ローカル動画ファイルのパス
        sample_every_n_frames: 何フレームおきに解析するか（負荷削減）
        min_detection_confidence: MediaPipe の検出信頼度しきい値

    Returns:
        PoseSequence

    Raises:
        PoseEstimationError: mediapipe / opencv が import できない場合
    """
    try:
        import cv2  # type: ignore
        import mediapipe as mp  # type: ignore
    except ImportError as exc:  # pragma: no cover - 環境依存
        raise PoseEstimationError("mediapipe / opencv-python がインストールされていません") from exc

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise PoseEstimationError(f"動画を開けません: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames: list[PoseFrame] = []
    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=min_detection_confidence,
    )

    try:
        frame_idx = 0
        while True:
            ok, image = cap.read()
            if not ok:
                break
            if frame_idx % sample_every_n_frames == 0:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                if result.pose_landmarks:
                    lms = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                        for lm in result.pose_landmarks.landmark
                    ]
                    frames.append(PoseFrame(landmarks=lms))
            frame_idx += 1
    finally:
        pose.close()
        cap.release()

    # サンプリング後の実効 FPS
    effective_fps = fps / sample_every_n_frames if sample_every_n_frames > 0 else fps

    return PoseSequence(
        frames=frames,
        fps=effective_fps,
        width=width,
        height=height,
        meta={"source_fps": fps, "sampled_every": sample_every_n_frames},
    )


def extract_pose_from_s3(s3_key: str) -> PoseSequence:
    """S3 の動画をダウンロードしてポーズ時系列を抽出する。"""
    local_path = _download_to_temp(s3_key)
    try:
        return extract_pose_from_file(local_path)
    finally:
        try:
            os.remove(local_path)
        except OSError:  # pragma: no cover
            logger.warning("一時ファイルの削除に失敗: %s", local_path)
