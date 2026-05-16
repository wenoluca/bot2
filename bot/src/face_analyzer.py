import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from dataclasses import dataclass, field
from typing import Optional
import math
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "face_landmarker.task")

GOLDEN_RATIO = 1.618033988749895


@dataclass
class FaceMetrics:
    # Core scores
    golden_ratio_score: float = 0.0
    symmetry_score: float = 0.0
    facial_thirds_score: float = 0.0
    canthal_tilt_degrees: float = 0.0
    canthal_tilt_score: float = 0.0
    jaw_score: float = 0.0
    overall_score: float = 0.0
    grade: str = "N/A"
    tier: str = "MTN"

    # Extra key-parameter scores
    eyes_score: float = 0.0
    nose_score: float = 0.0
    lips_score: float = 0.0
    cheekbones_score: float = 0.0
    eyebrows_score: float = 0.0
    balance_score: float = 0.0

    # Raw measurements (pixels)
    face_width: float = 0.0
    face_height: float = 0.0
    upper_third: float = 0.0
    middle_third: float = 0.0
    lower_third: float = 0.0
    left_eye_width: float = 0.0
    right_eye_width: float = 0.0
    mouth_width: float = 0.0
    nose_width: float = 0.0
    interpupillary_distance: float = 0.0

    details: dict = field(default_factory=dict)
    landmark_image: Optional[bytes] = None


def _dist(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _midpoint(p1, p2):
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def _ratio_score(value, ideal, tolerance=0.15):
    dev = abs(value - ideal) / ideal
    return round(max(0.0, 10.0 - dev / tolerance * 5.0), 2)


def _golden_ratio_score(a, b):
    if b == 0:
        return 0.0
    ratio = max(a, b) / min(a, b)
    deviation = abs(ratio - GOLDEN_RATIO)
    return round(max(0.0, 10.0 - deviation * 10.0), 2)


def _get_tier(score: float) -> str:
    if score >= 7.5:
        return "HTN"
    elif score >= 5.5:
        return "MTN"
    else:
        return "LTN"


def _get_grade(score: float) -> str:
    if score >= 9.5:
        return "SSS — Легендарная внешность"
    elif score >= 9.0:
        return "SS — Исключительная красота"
    elif score >= 8.5:
        return "S — Высокая привлекательность"
    elif score >= 8.0:
        return "A+ — Выше среднего"
    elif score >= 7.0:
        return "A — Привлекательный"
    elif score >= 6.0:
        return "B — Чуть выше нормы"
    elif score >= 5.0:
        return "C — Средний"
    elif score >= 4.0:
        return "D — Ниже среднего"
    else:
        return "E — Требует работы"


def _get_landmarker():
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)


def analyze_face(image_bytes: bytes) -> Optional[FaceMetrics]:
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return None

    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    with _get_landmarker() as landmarker:
        result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return None

    lms = result.face_landmarks[0]

    def pt(idx):
        lm = lms[idx]
        return (lm.x * w, lm.y * h)

    # ── Основные ориентиры ───────────────────────────────────────────────────
    left_cheek = pt(234)
    right_cheek = pt(454)
    face_width = _dist(left_cheek, right_cheek)

    chin = pt(152)
    forehead = pt(10)
    face_height = _dist(chin, forehead)

    # ── Золотое сечение ──────────────────────────────────────────────────────
    golden_ratio_score = _golden_ratio_score(face_height, face_width)

    # ── Трети лица ──────────────────────────────────────────────────────────
    brow_line = _midpoint(pt(107), pt(336))
    nose_base = pt(2)

    upper_third = _dist(forehead, brow_line)
    middle_third = _dist(brow_line, nose_base)
    lower_third = _dist(nose_base, chin)
    total_thirds = upper_third + middle_third + lower_third
    ideal_third = total_thirds / 3.0

    thirds_deviation = (
        abs(upper_third - ideal_third)
        + abs(middle_third - ideal_third)
        + abs(lower_third - ideal_third)
    ) / total_thirds
    thirds_score = round(max(0.0, 10.0 - thirds_deviation * 30.0), 2)

    # ── Симметрия ────────────────────────────────────────────────────────────
    nose_cx = pt(4)[0]

    left_eye_outer = pt(33)
    left_eye_inner = pt(133)
    right_eye_inner = pt(362)
    right_eye_outer = pt(263)

    left_eye_width = _dist(left_eye_outer, left_eye_inner)
    right_eye_width = _dist(right_eye_inner, right_eye_outer)
    eye_sym = 1 - abs(left_eye_width - right_eye_width) / max(left_eye_width, right_eye_width, 1)

    left_ck = abs(left_cheek[0] - nose_cx)
    right_ck = abs(right_cheek[0] - nose_cx)
    cheek_sym = 1 - abs(left_ck - right_ck) / max(left_ck, right_ck, 1)

    mouth_left = pt(61)
    mouth_right = pt(291)
    m_left_d = abs(mouth_left[0] - nose_cx)
    m_right_d = abs(mouth_right[0] - nose_cx)
    mouth_sym = 1 - abs(m_left_d - m_right_d) / max(m_left_d, m_right_d, 1)

    symmetry_score = round(((eye_sym + cheek_sym + mouth_sym) / 3) * 10.0, 2)

    # ── Кантальный тильт ─────────────────────────────────────────────────────
    left_tilt = math.degrees(math.atan2(
        left_eye_inner[1] - left_eye_outer[1],
        left_eye_outer[0] - left_eye_inner[0],
    ))
    right_tilt = math.degrees(math.atan2(
        right_eye_inner[1] - right_eye_outer[1],
        right_eye_outer[0] - right_eye_inner[0],
    ))
    canthal_tilt_degrees = round((left_tilt + right_tilt) / 2, 2)

    if 5 <= canthal_tilt_degrees <= 15:
        canthal_tilt_score = 10.0
    elif canthal_tilt_degrees > 0:
        canthal_tilt_score = max(0.0, 7.0 + canthal_tilt_degrees * 0.6)
    else:
        canthal_tilt_score = max(0.0, 7.0 + canthal_tilt_degrees * 0.5)
    canthal_tilt_score = round(min(10.0, canthal_tilt_score), 2)

    # ── Челюсть ──────────────────────────────────────────────────────────────
    jaw_width = _dist(pt(172), pt(397))
    jaw_to_cheek = jaw_width / face_width if face_width > 0 else 0
    jaw_score = round(max(0.0, 10.0 - abs(jaw_to_cheek - 0.75) * 30.0), 2)

    # ── IPD и нос ────────────────────────────────────────────────────────────
    left_pupil = _midpoint(pt(33), pt(133))
    right_pupil = _midpoint(pt(362), pt(263))
    ipd = _dist(left_pupil, right_pupil)
    ipd_ratio = ipd / face_width if face_width > 0 else 0

    nose_width = _dist(pt(129), pt(358))
    mouth_width = _dist(mouth_left, mouth_right)

    # ── Дополнительные метрики ───────────────────────────────────────────────
    # Глаза: ширина глаза ≈ 1/5 ширины лица
    ideal_eye_w = face_width / 5.0
    left_dev = abs(left_eye_width - ideal_eye_w) / ideal_eye_w
    right_dev = abs(right_eye_width - ideal_eye_w) / ideal_eye_w
    eyes_score = round(max(0.0, 10.0 - (left_dev + right_dev) * 12.0), 2)

    # Нос: ширина носа ≈ 1/5 ширины лица
    nose_dev = abs(nose_width - face_width / 5.0) / (face_width / 5.0)
    nose_score = round(max(0.0, 10.0 - nose_dev * 14.0), 2)

    # Губы: ширина рта ≈ IPD (межзрачковое расстояние)
    lips_ratio = mouth_width / ipd if ipd > 0 else 1.0
    lips_score = round(max(0.0, 10.0 - abs(lips_ratio - 1.0) * 14.0), 2)

    # Скулы: ширина скул / ширина челюсти ≈ 1.25–1.35
    cheek_jaw = face_width / jaw_width if jaw_width > 0 else 1.0
    cheekbones_score = round(max(0.0, 10.0 - abs(cheek_jaw - 1.30) * 20.0), 2)

    # Брови: расстояние бровь-глаз / высота лица ≈ 0.055–0.075
    brow_top = pt(107)
    eye_top = pt(159)
    brow_dist_ratio = _dist(brow_top, eye_top) / face_height if face_height > 0 else 0
    eyebrows_score = round(max(0.0, 10.0 - abs(brow_dist_ratio - 0.065) * 120.0), 2)

    # Баланс: средняя по трём опорным пропорциям
    balance_score = round((golden_ratio_score + symmetry_score + thirds_score) / 3.0, 2)

    # ── Итоговый балл ────────────────────────────────────────────────────────
    overall = round(
        golden_ratio_score * 0.20
        + symmetry_score * 0.20
        + thirds_score * 0.15
        + canthal_tilt_score * 0.15
        + jaw_score * 0.10
        + eyes_score * 0.07
        + nose_score * 0.05
        + lips_score * 0.04
        + cheekbones_score * 0.04,
        2,
    )

    grade = _get_grade(overall)
    tier = _get_tier(overall)

    # ── Аннотированное фото ──────────────────────────────────────────────────
    annotated = img.copy()
    _draw_overlay(annotated, lms, w, h, overall, tier)
    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])

    return FaceMetrics(
        golden_ratio_score=golden_ratio_score,
        symmetry_score=symmetry_score,
        facial_thirds_score=thirds_score,
        canthal_tilt_degrees=canthal_tilt_degrees,
        canthal_tilt_score=canthal_tilt_score,
        jaw_score=jaw_score,
        overall_score=overall,
        grade=grade,
        tier=tier,
        eyes_score=eyes_score,
        nose_score=nose_score,
        lips_score=lips_score,
        cheekbones_score=cheekbones_score,
        eyebrows_score=eyebrows_score,
        balance_score=balance_score,
        face_width=round(face_width, 1),
        face_height=round(face_height, 1),
        upper_third=round(upper_third, 1),
        middle_third=round(middle_third, 1),
        lower_third=round(lower_third, 1),
        left_eye_width=round(left_eye_width, 1),
        right_eye_width=round(right_eye_width, 1),
        mouth_width=round(mouth_width, 1),
        nose_width=round(nose_width, 1),
        interpupillary_distance=round(ipd, 1),
        details={
            "jaw_to_cheek_ratio": round(jaw_to_cheek, 3),
            "ipd_to_face_ratio": round(ipd_ratio, 3),
            "face_hw_ratio": round(face_height / face_width, 3) if face_width > 0 else 0,
            "upper_third_pct": round(upper_third / total_thirds * 100, 1),
            "middle_third_pct": round(middle_third / total_thirds * 100, 1),
            "lower_third_pct": round(lower_third / total_thirds * 100, 1),
            "eye_symmetry": round(eye_sym * 10, 2),
            "cheek_symmetry": round(cheek_sym * 10, 2),
            "mouth_symmetry": round(mouth_sym * 10, 2),
            "cheek_jaw_ratio": round(cheek_jaw, 3),
        },
        landmark_image=buf.tobytes(),
    )


def _draw_overlay(img, lms, w, h, score, tier):
    def pt(idx):
        lm = lms[idx]
        return (int(lm.x * w), int(lm.y * h))

    GOLD = (0, 210, 255)
    CYAN = (200, 230, 0)

    for idx_list in [
        [33, 7, 163, 144, 145, 153, 154, 155, 133],
        [362, 382, 381, 380, 374, 373, 390, 249, 263],
    ]:
        cv2.polylines(img, [np.array([pt(i) for i in idx_list], np.int32)], True, CYAN, 1)

    cv2.polylines(img, [np.array([pt(i) for i in [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]], np.int32)], True, GOLD, 1)
    cv2.polylines(img, [np.array([pt(i) for i in [168, 6, 197, 195, 5, 4]], np.int32)], False, CYAN, 1)

    jaw_idx = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,
               400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109,10]
    cv2.polylines(img, [np.array([pt(i) for i in jaw_idx], np.int32)], False, GOLD, 1)

    # Watermark only — score is shown in the PDF, not baked into the image
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (145, 28), (0, 0, 0), -1)
    img[:] = cv2.addWeighted(overlay, 0.55, img, 0.45, 0)
    cv2.putText(img, "facedex.ai", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, CYAN, 1)
