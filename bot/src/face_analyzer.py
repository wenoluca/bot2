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

# ── Нормы Лесли Фаркаса (мужчины) ────────────────────────────────────────────
# mean, effective_std
# ВАЖНО: публикационные std Фаркаса взяты из узкой однородной выборки.
# Реальное мировое разнообразие значительно шире, поэтому std умножены на 2.2
# чтобы ±1 "реальная σ" ≈ ±2.2 Farkas-σ. Иначе большинство нормальных лиц
# попадают в 3+ σ и уходят на минимум.
FARKAS = {
    "face_hw_ratio":        (0.896, 0.077),  # 0.035 × 2.2
    "vertical_balance":     (0.728, 0.110),  # 0.042 × 2.6 — шире норма для мужских лиц
    "cheek_jaw":            (1.356, 0.209),  # 0.095 × 2.2
    "eye_to_face":          (0.223, 0.040),  # 0.018 × 2.2
    "inner_eye_to_face":    (0.271, 0.085),  # шире std — MediaPipe inner corner варьируется
    "canthal_tilt":         (0.036, 0.055),  # 0.025 × 2.2
    "nose_to_face":         (0.234, 0.046),  # 0.021 × 2.2
    "mouth_to_face":        (0.403, 0.062),  # 0.028 × 2.2
    "nose_length":          (0.421, 0.112),  # 0.032 × 3.5 — более широкий диапазон нормы
    "chin_length":          (0.283, 0.060),  # 0.020 × 3.0 — более широкий диапазон
    "chin_contour":         (0.630, 0.132),  # 0.060 × 2.2
    "nose_to_mouth":        (0.583, 0.092),  # 0.042 × 2.2
    "biocular_width":       (0.713, 0.110),  # 0.050 × 2.2
    "forehead_width":       (0.919, 0.121),  # 0.055 × 2.2
    "lip_fullness":         (0.347, 0.062),  # 0.028 × 2.2
    "lip_ratio":            (0.639, 0.143),  # 0.065 × 2.2
    "jaw_to_mouth":         (1.810, 0.308),  # 0.140 × 2.2
    "eye_shape":            (0.285, 0.055),  # 0.025 × 2.2
    "brow_height":          (0.063, 0.026),  # 0.012 × 2.2
}


@dataclass
class FaceMetrics:
    # Core scores (old API — kept for compatibility)
    golden_ratio_score: float = 0.0
    symmetry_score: float = 0.0
    facial_thirds_score: float = 0.0
    canthal_tilt_degrees: float = 0.0
    canthal_tilt_score: float = 0.0
    jaw_score: float = 0.0
    overall_score: float = 0.0
    grade: str = "N/A"
    tier: str = "MTN"

    # Extra scores
    eyes_score: float = 0.0
    nose_score: float = 0.0
    lips_score: float = 0.0
    cheekbones_score: float = 0.0
    eyebrows_score: float = 0.0
    balance_score: float = 0.0

    # Gender estimate (heuristic, not guaranteed)
    likely_female: bool = False

    # Extended 20-metric scores
    face_proportions_score: float = 0.0      # H/W ratio
    vertical_balance_score: float = 0.0     # средняя/нижняя трети
    eye_distance_score: float = 0.0          # расстояние между глазами
    nose_length_score: float = 0.0           # длина носа
    chin_length_score: float = 0.0           # длина подбородка
    chin_contour_score: float = 0.0          # контур подбородка
    nose_to_mouth_score: float = 0.0         # нос к ширине рта
    biocular_score: float = 0.0              # биокулярная ширина
    forehead_score: float = 0.0              # ширина лба
    lip_fullness_score: float = 0.0          # полнота губ
    lip_ratio_score: float = 0.0             # пропорции губ
    jaw_to_mouth_score: float = 0.0          # челюсть к ширине рта
    eye_shape_score: float = 0.0             # форма глаз
    brow_height_score: float = 0.0           # высота бровей

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


def _sigma_score(value, mean, std, direction="both", min_score=4.5):
    """
    Оценка 4.5–10 по σ от нормы Фаркаса.

    Базовая точка: mean (Farkas avg) → 7.0 (нормальное/гармоничное лицо).
    Среднестатистическое лицо НЕ должно быть "ниже среднего" — оно и есть норма.

    direction="both":
        Симметричный штраф: −1.0 балла / σ.
        0σ=7.0 | 1σ=6.0 | 2σ=5.0 | 3σ=4.5(пол).

    direction="up"  (большее значение лучше — hunter eyes, широкая челюсть):
        Выше нормы → бонус +1.5/σ (до 10).
        Ниже нормы → мягкий штраф −0.6/σ (нейтральный ≠ плохо).

    direction="down" (меньшее значение лучше — узкий нос, V-подбородок):
        Ниже нормы → бонус +1.5/σ (до 10).
        Выше нормы → мягкий штраф −0.6/σ.

    Целевые диапазоны:
        Строго норма (0σ)      → 7.0
        Хорошее (1σ в нужную)  → 8.5
        Элитное (2σ в нужную)  → 10.0
        Нейтральное (1σ, both) → 6.0
        Минимум                → 4.5
    """
    if std == 0:
        return 7.0
    z = (value - mean) / std

    if direction == "both":
        score = 7.0 - abs(z) * 1.0

    elif direction == "up":
        if z >= 0:
            score = 7.0 + z * 1.5
        else:
            score = 7.0 + z * 0.6

    else:  # direction == "down"
        if z <= 0:
            score = 7.0 + (-z) * 1.5
        else:
            score = 7.0 - z * 0.6

    return round(max(min_score, min(10.0, score)), 2)


def _golden_ratio_score(a, b):
    if b == 0:
        return 5.0
    ratio = max(a, b) / min(a, b)
    deviation = abs(ratio - GOLDEN_RATIO)
    return round(max(2.0, 10.0 - deviation * 8.0), 2)


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
    left_cheek  = pt(234)
    right_cheek = pt(454)
    face_width  = _dist(left_cheek, right_cheek)

    chin     = pt(152)
    forehead = pt(10)
    face_height = _dist(chin, forehead)

    if face_width < 10 or face_height < 10:
        return None

    # ── Глаза ────────────────────────────────────────────────────────────────
    left_eye_outer  = pt(33)
    left_eye_inner  = pt(133)
    right_eye_inner = pt(362)
    right_eye_outer = pt(263)

    left_eye_width  = _dist(left_eye_outer, left_eye_inner)
    right_eye_width = _dist(right_eye_inner, right_eye_outer)
    avg_eye_width   = (left_eye_width + right_eye_width) / 2.0

    left_pupil  = _midpoint(pt(33), pt(133))
    right_pupil = _midpoint(pt(362), pt(263))
    ipd = _dist(left_pupil, right_pupil)

    # Высота глаза (верхнее и нижнее веко)
    left_eye_top    = pt(159)
    left_eye_bottom = pt(145)
    left_eye_height = _dist(left_eye_top, left_eye_bottom)

    # ── Нос ──────────────────────────────────────────────────────────────────
    nose_tip  = pt(4)
    nose_base = pt(2)
    nose_width = _dist(pt(129), pt(358))
    nose_length = _dist(pt(6), nose_base)   # переносица → основание носа

    # ── Рот ──────────────────────────────────────────────────────────────────
    mouth_left  = pt(61)
    mouth_right = pt(291)
    mouth_width = _dist(mouth_left, mouth_right)

    # Губы: высота верхней и нижней
    upper_lip_top    = pt(0)    # верх верхней губы
    upper_lip_bottom = pt(13)   # низ верхней губы
    lower_lip_top    = pt(14)   # верх нижней губы
    lower_lip_bottom = pt(17)   # низ нижней губы

    upper_lip_h = _dist(upper_lip_top, upper_lip_bottom)
    lower_lip_h = _dist(lower_lip_top, lower_lip_bottom)
    total_lip_h = upper_lip_h + lower_lip_h

    # ── Скулы и челюсть ──────────────────────────────────────────────────────
    jaw_left  = pt(172)
    jaw_right = pt(397)
    jaw_width = _dist(jaw_left, jaw_right)

    chin_narrow_left  = pt(175)
    chin_narrow_right = pt(396)

    # ── Брови ────────────────────────────────────────────────────────────────
    brow_line  = _midpoint(pt(107), pt(336))
    brow_top_l = pt(107)
    eye_top_l  = pt(159)

    # ── Лоб ──────────────────────────────────────────────────────────────────
    forehead_left  = pt(103)
    forehead_right = pt(332)
    forehead_width = _dist(forehead_left, forehead_right)

    # ── Трети лица ──────────────────────────────────────────────────────────
    upper_third  = _dist(forehead, brow_line)
    middle_third = _dist(brow_line, nose_base)
    lower_third  = _dist(nose_base, chin)
    total_thirds = upper_third + middle_third + lower_third

    # ── Симметрия ────────────────────────────────────────────────────────────
    nose_cx = nose_tip[0]

    eye_sym = 1 - abs(left_eye_width - right_eye_width) / max(left_eye_width, right_eye_width, 1)

    left_ck  = abs(left_cheek[0]  - nose_cx)
    right_ck = abs(right_cheek[0] - nose_cx)
    cheek_sym = 1 - abs(left_ck - right_ck) / max(left_ck, right_ck, 1)

    m_left_d  = abs(mouth_left[0]  - nose_cx)
    m_right_d = abs(mouth_right[0] - nose_cx)
    mouth_sym = 1 - abs(m_left_d - m_right_d) / max(m_left_d, m_right_d, 1)

    symmetry_raw = (eye_sym + cheek_sym + mouth_sym) / 3.0
    symmetry_score = round(max(2.0, min(10.0, symmetry_raw * 10.0 + 0.5)), 2)

    # ── Кантальный тильт (по нормализованному значению) ─────────────────────
    # Вектор от outer к inner для ЛЕВОГО глаза в пространстве (y вверх → negate image y)
    dx_l = left_eye_inner[0] - left_eye_outer[0]
    dy_l = -(left_eye_inner[1] - left_eye_outer[1])   # flip y for math coords
    left_tilt_rad = math.atan2(dy_l, dx_l)

    dx_r = right_eye_inner[0] - right_eye_outer[0]
    dy_r = -(right_eye_inner[1] - right_eye_outer[1])
    right_tilt_rad = math.atan2(dy_r, abs(dx_r))

    canthal_tilt_degrees = round(math.degrees((left_tilt_rad + right_tilt_rad) / 2), 2)

    # Нормализованный тильт (наклон / ширина глаза) для Farkas
    canthal_norm = math.tan(math.radians(abs(canthal_tilt_degrees))) if avg_eye_width > 0 else 0
    canthal_norm = canthal_norm if canthal_tilt_degrees >= 0 else -canthal_norm

    # Положительный тильт (hunter eyes) награждается
    canthal_tilt_score = _sigma_score(canthal_norm, FARKAS["canthal_tilt"][0],
                                      FARKAS["canthal_tilt"][1], direction="up")

    # ── Все соотношения для оценки ────────────────────────────────────────────
    hw_ratio         = face_height / face_width
    vert_balance     = middle_third / lower_third if lower_third > 0 else 0.728
    cheek_jaw_ratio  = face_width / jaw_width if jaw_width > 0 else 1.356
    eye_to_face      = avg_eye_width / face_width
    inner_eye_to_face = _dist(left_eye_inner, right_eye_inner) / face_width
    nose_to_face     = nose_width / face_width
    mouth_to_face    = mouth_width / face_width
    nose_len_ratio   = nose_length / face_height
    chin_len_ratio   = _dist(lower_lip_bottom, chin) / face_height

    chin_narrow_w    = _dist(chin_narrow_left, chin_narrow_right)
    chin_contour     = chin_narrow_w / jaw_width if jaw_width > 0 else 0.630

    nose_to_mouth    = nose_width / mouth_width if mouth_width > 0 else 0.583
    biocular_width   = _dist(left_eye_outer, right_eye_outer) / face_width
    forehead_ratio   = forehead_width / face_width

    lip_fullness     = total_lip_h / mouth_width if mouth_width > 0 else 0.347
    lip_ratio        = upper_lip_h / lower_lip_h if lower_lip_h > 0 else 0.639
    jaw_to_mouth_r   = jaw_width / mouth_width if mouth_width > 0 else 1.810

    eye_shape_r      = left_eye_height / left_eye_width if left_eye_width > 0 else 0.285
    brow_dist_r      = _dist(brow_top_l, eye_top_l) / face_height if face_height > 0 else 0.063

    thirds_dev = (
        abs(upper_third - total_thirds / 3)
        + abs(middle_third - total_thirds / 3)
        + abs(lower_third - total_thirds / 3)
    ) / total_thirds
    # По спецификации: отклонения до ~10% считаются нормой (не штрафуются сильно).
    # 0% отклонение → 9.5 (elite), 10% отклонение → 6.5 (норма), 20% → 3.5 (пол).
    thirds_score = round(max(3.5, 9.5 - thirds_dev * 30.0), 2)

    # ── Оценки по всем метрикам ───────────────────────────────────────────────
    #
    # direction:
    #   "both" — штраф в обе стороны от Farkas нормы
    #   "up"   — штраф только НИЖЕ нормы (высокое = хорошо для мужчин)
    #   "down" — штраф только ВЫШЕ нормы (низкое = хорошо для мужчин)
    #
    # Маскулинные направления:
    #   cheek_jaw (face_w/jaw_w): нижнее → шире челюсть → мужественнее → direction="down"
    #   jaw_to_mouth: выше → шире челюсть относительно рта → direction="up"
    #   canthal_tilt: выше (hunter eyes) → direction="up"  (уже задано выше)
    #   chin_contour: ниже → более V-образный подбородок → direction="down"
    #   nose_len: "both" — и слишком длинный, и слишком короткий нехорошо
    #
    golden_ratio_score      = _golden_ratio_score(face_height, face_width)
    # Длинное лицо (высокий hw_ratio) у мужчин маскулиннее → direction="up"
    face_proportions_score  = _sigma_score(hw_ratio,          *FARKAS["face_hw_ratio"],
                                           direction="up")
    # Vert balance = middle/lower. Ниже нормы = длиннее нижняя треть = мужественнее → direction="down"
    vertical_balance_score  = _sigma_score(vert_balance,      *FARKAS["vertical_balance"],
                                           direction="down")
    cheekbones_score        = _sigma_score(cheek_jaw_ratio,   *FARKAS["cheek_jaw"],
                                           direction="down")   # шире челюсть = лучше
    eyes_score              = _sigma_score(eye_to_face,       *FARKAS["eye_to_face"])
    eye_distance_score      = _sigma_score(inner_eye_to_face, *FARKAS["inner_eye_to_face"])
    nose_score              = _sigma_score(nose_to_face,      *FARKAS["nose_to_face"],
                                           direction="down")   # уже нос = лучше
    lips_score              = _sigma_score(mouth_to_face,     *FARKAS["mouth_to_face"])
    nose_length_score       = _sigma_score(nose_len_ratio,    *FARKAS["nose_length"])
    chin_length_score       = _sigma_score(chin_len_ratio,    *FARKAS["chin_length"],
                                           direction="up")     # выраженный подбородок = плюс
    chin_contour_score      = _sigma_score(chin_contour,      *FARKAS["chin_contour"],
                                           direction="down")   # более V = лучше
    nose_to_mouth_score     = _sigma_score(nose_to_mouth,     *FARKAS["nose_to_mouth"])
    biocular_score          = _sigma_score(biocular_width,    *FARKAS["biocular_width"])
    forehead_score          = _sigma_score(forehead_ratio,    *FARKAS["forehead_width"],
                                           direction="up")     # шире лоб = мужественнее
    lip_fullness_score      = _sigma_score(lip_fullness,      *FARKAS["lip_fullness"],
                                           direction="up")     # умеренный объём = плюс, тонкие = минус
    lip_ratio_score         = _sigma_score(lip_ratio,         *FARKAS["lip_ratio"])
    jaw_to_mouth_score      = _sigma_score(jaw_to_mouth_r,    *FARKAS["jaw_to_mouth"],
                                           direction="up")     # шире челюсть/рот = лучше
    eye_shape_score         = _sigma_score(eye_shape_r,       *FARKAS["eye_shape"])
    brow_height_score       = _sigma_score(brow_dist_r,       *FARKAS["brow_height"],
                                           direction="down")   # малое расстояние бровь-глаз = привлекательнее

    jaw_score = cheekbones_score  # синоним (уже направленный)

    eyebrows_score = brow_height_score
    balance_score  = round((golden_ratio_score + symmetry_score + thirds_score) / 3.0, 2)

    # ── Итоговый балл (взвешенное среднее 20 метрик) ─────────────────────────
    weights = {
        "symmetry":         0.12,
        "proportions":      0.08,
        "thirds":           0.07,
        "canthal":          0.10,
        "cheekbones":       0.08,
        "eyes":             0.06,
        "eye_distance":     0.05,
        "nose":             0.05,
        "mouth":            0.05,
        "nose_length":      0.04,
        "chin_length":      0.05,
        "chin_contour":     0.04,
        "nose_to_mouth":    0.04,
        "biocular":         0.04,
        "forehead":         0.03,
        "lip_fullness":     0.03,
        "lip_ratio":        0.02,
        "jaw_to_mouth":     0.03,
        "eye_shape":        0.05,
        "brow":             0.03,
        "golden_ratio":     0.03,
    }
    weighted = (
        symmetry_score          * weights["symmetry"]
        + face_proportions_score * weights["proportions"]
        + thirds_score           * weights["thirds"]
        + canthal_tilt_score     * weights["canthal"]
        + cheekbones_score       * weights["cheekbones"]
        + eyes_score             * weights["eyes"]
        + eye_distance_score     * weights["eye_distance"]
        + nose_score             * weights["nose"]
        + lips_score             * weights["mouth"]
        + nose_length_score      * weights["nose_length"]
        + chin_length_score      * weights["chin_length"]
        + chin_contour_score     * weights["chin_contour"]
        + nose_to_mouth_score    * weights["nose_to_mouth"]
        + biocular_score         * weights["biocular"]
        + forehead_score         * weights["forehead"]
        + lip_fullness_score     * weights["lip_fullness"]
        + lip_ratio_score        * weights["lip_ratio"]
        + jaw_to_mouth_score     * weights["jaw_to_mouth"]
        + eye_shape_score        * weights["eye_shape"]
        + brow_height_score      * weights["brow"]
        + golden_ratio_score     * weights["golden_ratio"]
    )
    weight_total = sum(weights.values())
    base_overall = weighted / weight_total

    # ── Бонус за межметрическую гармонию ─────────────────────────────────────
    # Когда несколько ключевых метрик одновременно высоки, лицо воспринимается
    # значительно привлекательнее, чем простое среднее — эффект синергии.
    all_metric_scores = [
        symmetry_score, face_proportions_score, thirds_score, canthal_tilt_score,
        cheekbones_score, eyes_score, eye_distance_score, nose_score, lips_score,
        nose_length_score, chin_length_score, chin_contour_score, nose_to_mouth_score,
        biocular_score, forehead_score, lip_fullness_score, lip_ratio_score,
        jaw_to_mouth_score, eye_shape_score, brow_height_score,
    ]
    above_norm = sum(1 for s in all_metric_scores if s >= 7.0)
    harmony_bonus = 0.0
    if above_norm >= 10:
        harmony_bonus = 0.25
    if above_norm >= 13:
        harmony_bonus = 0.50
    if above_norm >= 16:
        harmony_bonus = 0.80

    # Синергия пар: высокая симметрия + пропорции = запоминающееся гармоничное лицо
    if symmetry_score >= 8.0 and face_proportions_score >= 8.0:
        harmony_bonus += 0.20
    # Hunter eyes + скулы = мощный доминантный вид
    if canthal_tilt_score >= 8.0 and cheekbones_score >= 7.5:
        harmony_bonus += 0.15
    # Челюсть + подбородок = чёткий мужской контур
    if jaw_to_mouth_score >= 7.5 and chin_length_score >= 7.5:
        harmony_bonus += 0.10

    overall = round(max(1.5, min(10.0, base_overall + harmony_bonus)), 2)

    grade = _get_grade(overall)
    tier  = _get_tier(overall)

    # ── Эвристика пола ───────────────────────────────────────────────────────
    # Используем геометрические признаки, хорошо коррелирующие с полом:
    #   cheek_jaw_ratio  — у женщин выше (более овальное лицо)
    #   lip_fullness     — у женщин больше
    #   hw_ratio         — у женщин ниже (более круглое лицо)
    #   chin_contour     — у женщин меньше (более заострённый подбородок)
    #   canthal_tilt     — у женщин часто выше (более позитивный тильт)
    #   forehead_ratio   — у женщин меньше

    female_score = 0
    male_score   = 0

    # Скулы / челюсть
    if cheek_jaw_ratio > 1.52:   female_score += 2
    elif cheek_jaw_ratio < 1.28: male_score += 2
    else:                         male_score += 1   # в зоне мужской нормы

    # Полнота губ
    if lip_fullness > 0.40:      female_score += 2
    elif lip_fullness < 0.32:    male_score += 1

    # Соотношение высота/ширина лица
    if hw_ratio < 0.82:          female_score += 1   # более круглое
    elif hw_ratio > 0.90:        male_score += 1     # более вытянутое

    # Контур подбородка (сужение к подбородку)
    if chin_contour < 0.57:      female_score += 1
    elif chin_contour > 0.66:    male_score += 1

    # Кантальный тильт
    if canthal_tilt_degrees > 4.0:  female_score += 1
    elif canthal_tilt_degrees < 0:  male_score += 1

    # Ширина лба
    if forehead_ratio < 0.87:    female_score += 1
    elif forehead_ratio > 0.93:  male_score += 1

    # Форма глаза (более округлые = женские)
    if eye_shape_r > 0.32:       female_score += 1
    elif eye_shape_r < 0.24:     male_score += 1

    # Решение: помечаем «вероятно женщина» только при явном перевесе
    likely_female = (female_score >= 4) and (female_score > male_score + 1)

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
        likely_female=likely_female,
        eyes_score=eyes_score,
        nose_score=nose_score,
        lips_score=lips_score,
        cheekbones_score=cheekbones_score,
        eyebrows_score=brow_height_score,
        balance_score=balance_score,
        # Extended
        face_proportions_score=face_proportions_score,
        vertical_balance_score=vertical_balance_score,
        eye_distance_score=eye_distance_score,
        nose_length_score=nose_length_score,
        chin_length_score=chin_length_score,
        chin_contour_score=chin_contour_score,
        nose_to_mouth_score=nose_to_mouth_score,
        biocular_score=biocular_score,
        forehead_score=forehead_score,
        lip_fullness_score=lip_fullness_score,
        lip_ratio_score=lip_ratio_score,
        jaw_to_mouth_score=jaw_to_mouth_score,
        eye_shape_score=eye_shape_score,
        brow_height_score=brow_height_score,
        # Raw
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
            "jaw_to_cheek_ratio":   round(cheek_jaw_ratio, 3),
            "ipd_to_face_ratio":    round(ipd / face_width, 3),
            "face_hw_ratio":        round(hw_ratio, 3),
            "upper_third_pct":      round(upper_third / total_thirds * 100, 1),
            "middle_third_pct":     round(middle_third / total_thirds * 100, 1),
            "lower_third_pct":      round(lower_third / total_thirds * 100, 1),
            "eye_symmetry":         round(eye_sym * 10, 2),
            "cheek_symmetry":       round(cheek_sym * 10, 2),
            "mouth_symmetry":       round(mouth_sym * 10, 2),
            "cheek_jaw_ratio":      round(cheek_jaw_ratio, 3),
            "eye_to_face":          round(eye_to_face, 3),
            "nose_to_face":         round(nose_to_face, 3),
            "mouth_to_face":        round(mouth_to_face, 3),
            "inner_eye_to_face":    round(inner_eye_to_face, 3),
            "biocular_width":       round(biocular_width, 3),
            "forehead_ratio":       round(forehead_ratio, 3),
            "nose_len_ratio":       round(nose_len_ratio, 3),
            "chin_len_ratio":       round(chin_len_ratio, 3),
            "chin_contour":         round(chin_contour, 3),
            "nose_to_mouth":        round(nose_to_mouth, 3),
            "lip_fullness":         round(lip_fullness, 3),
            "lip_ratio":            round(lip_ratio, 3),
            "jaw_to_mouth":         round(jaw_to_mouth_r, 3),
            "eye_shape":            round(eye_shape_r, 3),
            "brow_dist_ratio":      round(brow_dist_r, 3),
            "vert_balance":         round(vert_balance, 3),
            "canthal_norm":         round(canthal_norm, 3),
        },
        landmark_image=buf.tobytes(),
    )


def _draw_dashed_line(img, pt1, pt2, color, thickness=1, dash=8, gap=5):
    """Draw a dashed line between two points."""
    dx = pt2[0] - pt1[0]
    dy = pt2[1] - pt1[1]
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1:
        return
    step = dash + gap
    n = int(dist / step)
    for i in range(n + 1):
        t0 = i * step / dist
        t1 = min(1.0, (i * step + dash) / dist)
        x0 = int(pt1[0] + dx * t0)
        y0 = int(pt1[1] + dy * t0)
        x1 = int(pt1[0] + dx * t1)
        y1 = int(pt1[1] + dy * t1)
        cv2.line(img, (x0, y0), (x1, y1), color, thickness)


def _draw_overlay(img, lms, w, h, score, tier):
    """
    Рисует сетку измерений Фаркаса на тёмном фоне (без фото лица).
    Стиль: пунктирные радиальные линии от ключевых точек, контуры глаз/носа/рта.
    """
    def pt(idx):
        lm = lms[idx]
        return (int(lm.x * w), int(lm.y * h))

    # ── Затемнённая копия фото (лицо видно, сетка поверх) ──────────────────
    canvas = cv2.addWeighted(img, 0.55, np.zeros_like(img), 0.45, 0)

    # Цвета (BGR)
    PINK   = (147, 110, 210)   # розово-лавандовый — основные линии
    BRIGHT = (180, 140, 255)   # ярко-розовый — контуры
    GOLD   = (50,  185, 210)   # золотисто-жёлтый — нос, брови, рот
    DIM    = (55,  55,  70)    # тёмный — контур лица, оси

    # ── Ключевые точки ────────────────────────────────────────────────────────
    nose_tip       = pt(4)
    nose_base      = pt(2)
    nose_bridge    = pt(6)
    left_eye_out   = pt(33)
    left_eye_in    = pt(133)
    right_eye_in   = pt(362)
    right_eye_out  = pt(263)
    left_brow_out  = pt(70)
    left_brow_in   = pt(107)
    right_brow_in  = pt(336)
    right_brow_out = pt(300)
    mouth_left     = pt(61)
    mouth_right    = pt(291)
    chin           = pt(152)
    forehead       = pt(10)
    left_cheek     = pt(234)
    right_cheek    = pt(454)
    left_jaw       = pt(172)
    right_jaw      = pt(397)

    brow_mid = (
        (left_brow_in[0] + right_brow_in[0]) // 2,
        (left_brow_in[1] + right_brow_in[1]) // 2,
    )
    mouth_mid = (
        (mouth_left[0] + mouth_right[0]) // 2,
        (mouth_left[1] + mouth_right[1]) // 2,
    )

    # ── 1. Контур лица (силуэт) — очень тонкий ──────────────────────────────
    jaw_idx = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,
               400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109,10]
    cv2.polylines(canvas, [np.array([pt(i) for i in jaw_idx], np.int32)], False, DIM, 1)

    # ── 2. Вертикальная ось симметрии ────────────────────────────────────────
    cx = nose_tip[0]
    _draw_dashed_line(canvas, (cx, forehead[1] - 10), (cx, chin[1] + 10), DIM, 1, 12, 6)

    # ── 3. Горизонтальные линии уровней (трети) ──────────────────────────────
    xl, xr = left_cheek[0] - 15, right_cheek[0] + 15
    for y in [brow_mid[1], nose_base[1], mouth_mid[1]]:
        _draw_dashed_line(canvas, (xl, y), (xr, y), DIM, 1, 10, 6)

    # ── 4. Радиальные линии от кончика носа ──────────────────────────────────
    radial_from_tip = [
        left_eye_out, left_eye_in, right_eye_in, right_eye_out,
        left_brow_out, left_brow_in, right_brow_in, right_brow_out,
        mouth_left, mouth_right,
        chin, forehead,
        left_cheek, right_cheek,
    ]
    for tgt in radial_from_tip:
        _draw_dashed_line(canvas, nose_tip, tgt, PINK, 1, 7, 5)

    # ── 5. Радиальные линии от основания носа ────────────────────────────────
    for tgt in [mouth_left, mouth_right, chin, left_jaw, right_jaw,
                left_cheek, right_cheek]:
        _draw_dashed_line(canvas, nose_base, tgt, BRIGHT, 1, 5, 4)

    # ── 6. Контуры глаз ──────────────────────────────────────────────────────
    for eye_pts in [
        [33, 7, 163, 144, 145, 153, 154, 155, 133],
        [362, 382, 381, 380, 374, 373, 390, 249, 263],
    ]:
        cv2.polylines(canvas, [np.array([pt(i) for i in eye_pts], np.int32)], True, BRIGHT, 1)

    # ── 7. Нос (переносица → кончик) ─────────────────────────────────────────
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in [168, 6, 197, 195, 5, 4]], np.int32)],
                  False, GOLD, 1)
    # Крылья носа
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in [129, 102, 49, 48, 115]], np.int32)],
                  False, GOLD, 1)
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in [358, 331, 279, 278, 344]], np.int32)],
                  False, GOLD, 1)

    # ── 8. Брови ─────────────────────────────────────────────────────────────
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in [70, 63, 105, 66, 107]], np.int32)],
                  False, GOLD, 1)
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in [336, 296, 334, 293, 300]], np.int32)],
                  False, GOLD, 1)

    # ── 9. Губы ───────────────────────────────────────────────────────────────
    cv2.polylines(canvas,
                  [np.array([pt(i) for i in
                             [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]],
                            np.int32)],
                  True, GOLD, 1)

    # ── 10. Ключевые точки (узловые) ─────────────────────────────────────────
    key_pts = [nose_tip, nose_base, left_eye_in, right_eye_in,
               left_eye_out, right_eye_out, mouth_left, mouth_right,
               chin, brow_mid]
    for kp in key_pts:
        cv2.circle(canvas, kp, 3, BRIGHT, -1)
        cv2.circle(canvas, kp, 5, PINK, 1)

    # ── 11. Ватермарк ─────────────────────────────────────────────────────────
    cv2.putText(canvas, "FACEDEX", (8, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, DIM, 1)

    img[:] = canvas
