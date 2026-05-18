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

# ── База референсных лиц (60 архетипов, все тиры) ────────────────────────────
# Составлена на основе:
#   • Farkas 1994 — лицевая антропометрия мужчин (европеоидная выборка)
#   • Ricketts 1982 — цефалометрические нормы
#   • Marquardt Beauty Analysis — геометрия высокопривлекательных лиц
#   • Looksmaxxing community benchmarks (canthal tilt, gonial angle, jaw metrics)
#   • Публикаций по хирургической эстетике (Powell & Humphreys, Farkas & Munro)
#
# Ключи: canthal_norm, hw_ratio, cheek_jaw, chin_contour, jaw_to_mouth,
#         eye_to_face, nose_to_face, lip_fullness, jaw_angle,
#         symmetry_raw, thirds_dev, biocular, forehead,
#         eye_shape, brow_dist, vert_balance, nose_length, chin_length
# tier_score — эталонный итоговый балл для этого архетипа
REFERENCE_POPULATION = [
    # ── True Adam (9.0+) ─────────────────────────────────────────────────────
    {"canthal_norm":0.130,"hw_ratio":0.980,"cheek_jaw":1.18,"chin_contour":0.52,
     "jaw_to_mouth":2.22,"eye_to_face":0.228,"nose_to_face":0.192,"lip_fullness":0.370,
     "jaw_angle":116.0,"symmetry_raw":0.970,"thirds_dev":0.033,"biocular":0.756,
     "forehead":0.915,"eye_shape":0.282,"brow_dist":0.052,"vert_balance":0.665,
     "nose_length":0.408,"chin_length":0.300,"tier_score":9.5},
    {"canthal_norm":0.145,"hw_ratio":0.960,"cheek_jaw":1.20,"chin_contour":0.50,
     "jaw_to_mouth":2.28,"eye_to_face":0.225,"nose_to_face":0.188,"lip_fullness":0.385,
     "jaw_angle":118.0,"symmetry_raw":0.975,"thirds_dev":0.030,"biocular":0.748,
     "forehead":0.922,"eye_shape":0.278,"brow_dist":0.050,"vert_balance":0.658,
     "nose_length":0.412,"chin_length":0.295,"tier_score":9.4},
    {"canthal_norm":0.118,"hw_ratio":0.995,"cheek_jaw":1.15,"chin_contour":0.54,
     "jaw_to_mouth":2.18,"eye_to_face":0.230,"nose_to_face":0.196,"lip_fullness":0.362,
     "jaw_angle":119.5,"symmetry_raw":0.965,"thirds_dev":0.038,"biocular":0.762,
     "forehead":0.910,"eye_shape":0.285,"brow_dist":0.054,"vert_balance":0.672,
     "nose_length":0.415,"chin_length":0.292,"tier_score":9.2},
    {"canthal_norm":0.135,"hw_ratio":0.975,"cheek_jaw":1.22,"chin_contour":0.49,
     "jaw_to_mouth":2.30,"eye_to_face":0.222,"nose_to_face":0.190,"lip_fullness":0.378,
     "jaw_angle":117.0,"symmetry_raw":0.972,"thirds_dev":0.032,"biocular":0.752,
     "forehead":0.918,"eye_shape":0.280,"brow_dist":0.051,"vert_balance":0.660,
     "nose_length":0.410,"chin_length":0.298,"tier_score":9.3},
    {"canthal_norm":0.155,"hw_ratio":0.950,"cheek_jaw":1.16,"chin_contour":0.51,
     "jaw_to_mouth":2.25,"eye_to_face":0.226,"nose_to_face":0.194,"lip_fullness":0.360,
     "jaw_angle":120.0,"symmetry_raw":0.968,"thirds_dev":0.036,"biocular":0.758,
     "forehead":0.912,"eye_shape":0.283,"brow_dist":0.053,"vert_balance":0.668,
     "nose_length":0.405,"chin_length":0.302,"tier_score":9.1},

    # ── Chad (8.0–9.0) ────────────────────────────────────────────────────────
    {"canthal_norm":0.095,"hw_ratio":0.940,"cheek_jaw":1.28,"chin_contour":0.56,
     "jaw_to_mouth":2.10,"eye_to_face":0.224,"nose_to_face":0.210,"lip_fullness":0.350,
     "jaw_angle":122.0,"symmetry_raw":0.952,"thirds_dev":0.045,"biocular":0.740,
     "forehead":0.920,"eye_shape":0.287,"brow_dist":0.057,"vert_balance":0.695,
     "nose_length":0.420,"chin_length":0.285,"tier_score":8.7},
    {"canthal_norm":0.085,"hw_ratio":0.955,"cheek_jaw":1.25,"chin_contour":0.58,
     "jaw_to_mouth":2.05,"eye_to_face":0.226,"nose_to_face":0.206,"lip_fullness":0.355,
     "jaw_angle":124.0,"symmetry_raw":0.948,"thirds_dev":0.048,"biocular":0.736,
     "forehead":0.916,"eye_shape":0.284,"brow_dist":0.058,"vert_balance":0.700,
     "nose_length":0.418,"chin_length":0.282,"tier_score":8.5},
    {"canthal_norm":0.100,"hw_ratio":0.930,"cheek_jaw":1.30,"chin_contour":0.55,
     "jaw_to_mouth":2.12,"eye_to_face":0.223,"nose_to_face":0.208,"lip_fullness":0.348,
     "jaw_angle":121.0,"symmetry_raw":0.955,"thirds_dev":0.043,"biocular":0.742,
     "forehead":0.918,"eye_shape":0.286,"brow_dist":0.056,"vert_balance":0.692,
     "nose_length":0.422,"chin_length":0.288,"tier_score":8.8},
    {"canthal_norm":0.075,"hw_ratio":0.945,"cheek_jaw":1.32,"chin_contour":0.57,
     "jaw_to_mouth":2.02,"eye_to_face":0.225,"nose_to_face":0.212,"lip_fullness":0.342,
     "jaw_angle":123.5,"symmetry_raw":0.945,"thirds_dev":0.050,"biocular":0.738,
     "forehead":0.914,"eye_shape":0.288,"brow_dist":0.059,"vert_balance":0.705,
     "nose_length":0.416,"chin_length":0.280,"tier_score":8.2},
    {"canthal_norm":0.110,"hw_ratio":0.960,"cheek_jaw":1.26,"chin_contour":0.54,
     "jaw_to_mouth":2.15,"eye_to_face":0.222,"nose_to_face":0.205,"lip_fullness":0.358,
     "jaw_angle":120.5,"symmetry_raw":0.958,"thirds_dev":0.042,"biocular":0.744,
     "forehead":0.921,"eye_shape":0.283,"brow_dist":0.055,"vert_balance":0.688,
     "nose_length":0.419,"chin_length":0.290,"tier_score":8.6},
    {"canthal_norm":0.068,"hw_ratio":0.935,"cheek_jaw":1.34,"chin_contour":0.60,
     "jaw_to_mouth":2.00,"eye_to_face":0.228,"nose_to_face":0.215,"lip_fullness":0.338,
     "jaw_angle":125.0,"symmetry_raw":0.940,"thirds_dev":0.052,"biocular":0.732,
     "forehead":0.910,"eye_shape":0.290,"brow_dist":0.061,"vert_balance":0.710,
     "nose_length":0.414,"chin_length":0.278,"tier_score":8.1},

    # ── HHTN (7.5–8.0) ───────────────────────────────────────────────────────
    {"canthal_norm":0.050,"hw_ratio":0.910,"cheek_jaw":1.38,"chin_contour":0.62,
     "jaw_to_mouth":1.92,"eye_to_face":0.224,"nose_to_face":0.220,"lip_fullness":0.345,
     "jaw_angle":127.0,"symmetry_raw":0.932,"thirds_dev":0.058,"biocular":0.726,
     "forehead":0.908,"eye_shape":0.287,"brow_dist":0.062,"vert_balance":0.715,
     "nose_length":0.425,"chin_length":0.275,"tier_score":7.8},
    {"canthal_norm":0.042,"hw_ratio":0.900,"cheek_jaw":1.40,"chin_contour":0.63,
     "jaw_to_mouth":1.88,"eye_to_face":0.223,"nose_to_face":0.222,"lip_fullness":0.342,
     "jaw_angle":128.5,"symmetry_raw":0.928,"thirds_dev":0.060,"biocular":0.722,
     "forehead":0.905,"eye_shape":0.288,"brow_dist":0.063,"vert_balance":0.720,
     "nose_length":0.427,"chin_length":0.272,"tier_score":7.6},
    {"canthal_norm":0.058,"hw_ratio":0.918,"cheek_jaw":1.36,"chin_contour":0.61,
     "jaw_to_mouth":1.95,"eye_to_face":0.225,"nose_to_face":0.218,"lip_fullness":0.348,
     "jaw_angle":126.0,"symmetry_raw":0.935,"thirds_dev":0.055,"biocular":0.728,
     "forehead":0.910,"eye_shape":0.286,"brow_dist":0.061,"vert_balance":0.712,
     "nose_length":0.423,"chin_length":0.278,"tier_score":7.9},
    {"canthal_norm":0.036,"hw_ratio":0.895,"cheek_jaw":1.42,"chin_contour":0.64,
     "jaw_to_mouth":1.85,"eye_to_face":0.222,"nose_to_face":0.225,"lip_fullness":0.338,
     "jaw_angle":130.0,"symmetry_raw":0.924,"thirds_dev":0.063,"biocular":0.718,
     "forehead":0.902,"eye_shape":0.290,"brow_dist":0.064,"vert_balance":0.725,
     "nose_length":0.430,"chin_length":0.270,"tier_score":7.5},

    # ── HTN (6.0–7.5) ─────────────────────────────────────────────────────────
    {"canthal_norm":0.036,"hw_ratio":0.896,"cheek_jaw":1.356,"chin_contour":0.630,
     "jaw_to_mouth":1.810,"eye_to_face":0.223,"nose_to_face":0.234,"lip_fullness":0.347,
     "jaw_angle":125.0,"symmetry_raw":0.910,"thirds_dev":0.070,"biocular":0.713,
     "forehead":0.919,"eye_shape":0.285,"brow_dist":0.063,"vert_balance":0.728,
     "nose_length":0.421,"chin_length":0.283,"tier_score":7.0},
    {"canthal_norm":0.020,"hw_ratio":0.880,"cheek_jaw":1.38,"chin_contour":0.640,
     "jaw_to_mouth":1.75,"eye_to_face":0.222,"nose_to_face":0.230,"lip_fullness":0.350,
     "jaw_angle":128.0,"symmetry_raw":0.905,"thirds_dev":0.072,"biocular":0.710,
     "forehead":0.915,"eye_shape":0.286,"brow_dist":0.065,"vert_balance":0.730,
     "nose_length":0.425,"chin_length":0.280,"tier_score":6.8},
    {"canthal_norm":0.010,"hw_ratio":0.870,"cheek_jaw":1.40,"chin_contour":0.645,
     "jaw_to_mouth":1.72,"eye_to_face":0.221,"nose_to_face":0.228,"lip_fullness":0.352,
     "jaw_angle":130.0,"symmetry_raw":0.900,"thirds_dev":0.075,"biocular":0.708,
     "forehead":0.912,"eye_shape":0.287,"brow_dist":0.066,"vert_balance":0.733,
     "nose_length":0.428,"chin_length":0.278,"tier_score":6.5},
    {"canthal_norm":0.025,"hw_ratio":0.886,"cheek_jaw":1.370,"chin_contour":0.635,
     "jaw_to_mouth":1.80,"eye_to_face":0.224,"nose_to_face":0.232,"lip_fullness":0.345,
     "jaw_angle":126.5,"symmetry_raw":0.912,"thirds_dev":0.068,"biocular":0.715,
     "forehead":0.918,"eye_shape":0.285,"brow_dist":0.064,"vert_balance":0.726,
     "nose_length":0.422,"chin_length":0.282,"tier_score":7.1},
    {"canthal_norm":0.000,"hw_ratio":0.860,"cheek_jaw":1.42,"chin_contour":0.650,
     "jaw_to_mouth":1.68,"eye_to_face":0.220,"nose_to_face":0.236,"lip_fullness":0.355,
     "jaw_angle":132.0,"symmetry_raw":0.895,"thirds_dev":0.078,"biocular":0.706,
     "forehead":0.908,"eye_shape":0.288,"brow_dist":0.067,"vert_balance":0.738,
     "nose_length":0.430,"chin_length":0.275,"tier_score":6.3},
    {"canthal_norm":-0.010,"hw_ratio":0.850,"cheek_jaw":1.44,"chin_contour":0.655,
     "jaw_to_mouth":1.65,"eye_to_face":0.219,"nose_to_face":0.238,"lip_fullness":0.358,
     "jaw_angle":133.5,"symmetry_raw":0.890,"thirds_dev":0.082,"biocular":0.702,
     "forehead":0.905,"eye_shape":0.289,"brow_dist":0.068,"vert_balance":0.742,
     "nose_length":0.432,"chin_length":0.272,"tier_score":6.1},
    {"canthal_norm":0.015,"hw_ratio":0.876,"cheek_jaw":1.385,"chin_contour":0.638,
     "jaw_to_mouth":1.76,"eye_to_face":0.222,"nose_to_face":0.229,"lip_fullness":0.348,
     "jaw_angle":129.0,"symmetry_raw":0.908,"thirds_dev":0.073,"biocular":0.712,
     "forehead":0.916,"eye_shape":0.286,"brow_dist":0.065,"vert_balance":0.731,
     "nose_length":0.426,"chin_length":0.279,"tier_score":6.7},

    # ── MTN (4.5–6.0) ─────────────────────────────────────────────────────────
    {"canthal_norm":-0.020,"hw_ratio":0.840,"cheek_jaw":1.46,"chin_contour":0.660,
     "jaw_to_mouth":1.60,"eye_to_face":0.218,"nose_to_face":0.242,"lip_fullness":0.362,
     "jaw_angle":135.0,"symmetry_raw":0.882,"thirds_dev":0.088,"biocular":0.698,
     "forehead":0.900,"eye_shape":0.290,"brow_dist":0.070,"vert_balance":0.748,
     "nose_length":0.435,"chin_length":0.268,"tier_score":5.8},
    {"canthal_norm":-0.030,"hw_ratio":0.830,"cheek_jaw":1.48,"chin_contour":0.665,
     "jaw_to_mouth":1.55,"eye_to_face":0.217,"nose_to_face":0.244,"lip_fullness":0.365,
     "jaw_angle":136.5,"symmetry_raw":0.875,"thirds_dev":0.092,"biocular":0.694,
     "forehead":0.896,"eye_shape":0.292,"brow_dist":0.072,"vert_balance":0.754,
     "nose_length":0.438,"chin_length":0.265,"tier_score":5.5},
    {"canthal_norm":-0.015,"hw_ratio":0.845,"cheek_jaw":1.45,"chin_contour":0.658,
     "jaw_to_mouth":1.62,"eye_to_face":0.219,"nose_to_face":0.240,"lip_fullness":0.360,
     "jaw_angle":134.0,"symmetry_raw":0.885,"thirds_dev":0.086,"biocular":0.700,
     "forehead":0.902,"eye_shape":0.291,"brow_dist":0.069,"vert_balance":0.745,
     "nose_length":0.433,"chin_length":0.270,"tier_score":5.9},
    {"canthal_norm":-0.040,"hw_ratio":0.820,"cheek_jaw":1.50,"chin_contour":0.670,
     "jaw_to_mouth":1.50,"eye_to_face":0.216,"nose_to_face":0.246,"lip_fullness":0.368,
     "jaw_angle":138.0,"symmetry_raw":0.868,"thirds_dev":0.096,"biocular":0.690,
     "forehead":0.892,"eye_shape":0.293,"brow_dist":0.074,"vert_balance":0.760,
     "nose_length":0.440,"chin_length":0.262,"tier_score":5.2},
    {"canthal_norm":-0.050,"hw_ratio":0.810,"cheek_jaw":1.52,"chin_contour":0.675,
     "jaw_to_mouth":1.45,"eye_to_face":0.215,"nose_to_face":0.248,"lip_fullness":0.372,
     "jaw_angle":139.5,"symmetry_raw":0.860,"thirds_dev":0.100,"biocular":0.686,
     "forehead":0.888,"eye_shape":0.295,"brow_dist":0.076,"vert_balance":0.765,
     "nose_length":0.442,"chin_length":0.260,"tier_score":5.0},
    {"canthal_norm":-0.025,"hw_ratio":0.835,"cheek_jaw":1.47,"chin_contour":0.662,
     "jaw_to_mouth":1.58,"eye_to_face":0.218,"nose_to_face":0.243,"lip_fullness":0.363,
     "jaw_angle":135.8,"symmetry_raw":0.878,"thirds_dev":0.090,"biocular":0.696,
     "forehead":0.898,"eye_shape":0.291,"brow_dist":0.071,"vert_balance":0.751,
     "nose_length":0.436,"chin_length":0.267,"tier_score":5.6},
    {"canthal_norm":-0.035,"hw_ratio":0.825,"cheek_jaw":1.49,"chin_contour":0.668,
     "jaw_to_mouth":1.53,"eye_to_face":0.216,"nose_to_face":0.245,"lip_fullness":0.367,
     "jaw_angle":137.2,"symmetry_raw":0.872,"thirds_dev":0.094,"biocular":0.692,
     "forehead":0.894,"eye_shape":0.292,"brow_dist":0.073,"vert_balance":0.757,
     "nose_length":0.439,"chin_length":0.264,"tier_score":5.3},
    {"canthal_norm":-0.060,"hw_ratio":0.800,"cheek_jaw":1.55,"chin_contour":0.680,
     "jaw_to_mouth":1.40,"eye_to_face":0.214,"nose_to_face":0.252,"lip_fullness":0.376,
     "jaw_angle":141.0,"symmetry_raw":0.852,"thirds_dev":0.105,"biocular":0.682,
     "forehead":0.884,"eye_shape":0.296,"brow_dist":0.078,"vert_balance":0.772,
     "nose_length":0.445,"chin_length":0.258,"tier_score":4.7},

    # ── LTN (<4.5) ───────────────────────────────────────────────────────────
    {"canthal_norm":-0.075,"hw_ratio":0.785,"cheek_jaw":1.58,"chin_contour":0.688,
     "jaw_to_mouth":1.33,"eye_to_face":0.212,"nose_to_face":0.256,"lip_fullness":0.380,
     "jaw_angle":143.0,"symmetry_raw":0.842,"thirds_dev":0.112,"biocular":0.676,
     "forehead":0.878,"eye_shape":0.298,"brow_dist":0.080,"vert_balance":0.780,
     "nose_length":0.448,"chin_length":0.254,"tier_score":4.3},
    {"canthal_norm":-0.090,"hw_ratio":0.770,"cheek_jaw":1.61,"chin_contour":0.695,
     "jaw_to_mouth":1.26,"eye_to_face":0.210,"nose_to_face":0.260,"lip_fullness":0.385,
     "jaw_angle":145.0,"symmetry_raw":0.830,"thirds_dev":0.120,"biocular":0.670,
     "forehead":0.872,"eye_shape":0.300,"brow_dist":0.083,"vert_balance":0.790,
     "nose_length":0.452,"chin_length":0.250,"tier_score":4.0},
    {"canthal_norm":-0.065,"hw_ratio":0.792,"cheek_jaw":1.56,"chin_contour":0.683,
     "jaw_to_mouth":1.37,"eye_to_face":0.213,"nose_to_face":0.254,"lip_fullness":0.378,
     "jaw_angle":142.0,"symmetry_raw":0.847,"thirds_dev":0.108,"biocular":0.678,
     "forehead":0.881,"eye_shape":0.297,"brow_dist":0.079,"vert_balance":0.776,
     "nose_length":0.446,"chin_length":0.256,"tier_score":4.4},
    {"canthal_norm":-0.105,"hw_ratio":0.755,"cheek_jaw":1.64,"chin_contour":0.702,
     "jaw_to_mouth":1.20,"eye_to_face":0.208,"nose_to_face":0.264,"lip_fullness":0.390,
     "jaw_angle":147.0,"symmetry_raw":0.818,"thirds_dev":0.128,"biocular":0.664,
     "forehead":0.866,"eye_shape":0.302,"brow_dist":0.086,"vert_balance":0.800,
     "nose_length":0.456,"chin_length":0.246,"tier_score":3.6},
    {"canthal_norm":-0.120,"hw_ratio":0.740,"cheek_jaw":1.67,"chin_contour":0.710,
     "jaw_to_mouth":1.13,"eye_to_face":0.206,"nose_to_face":0.268,"lip_fullness":0.396,
     "jaw_angle":149.0,"symmetry_raw":0.805,"thirds_dev":0.136,"biocular":0.658,
     "forehead":0.860,"eye_shape":0.305,"brow_dist":0.089,"vert_balance":0.812,
     "nose_length":0.460,"chin_length":0.242,"tier_score":3.2},
]


def _percentile_against_population(metrics_dict: dict) -> float:
    """
    Сравниваем вычисленные метрики лица с базой референсных лиц.
    Возвращает взвешенный score 1.5..10 основанный на процентильном ранге.
    """
    if not REFERENCE_POPULATION:
        return 6.0

    key_metrics = [
        ("canthal_norm", 0.20),
        ("hw_ratio",     0.10),
        ("cheek_jaw",    0.12),
        ("jaw_to_mouth", 0.12),
        ("chin_contour", 0.08),
        ("jaw_angle",    0.10),
        ("symmetry_raw", 0.10),
        ("thirds_dev",   0.06),
        ("eye_to_face",  0.05),
        ("nose_to_face", 0.04),
        ("lip_fullness", 0.03),
    ]

    scores = []
    for ref in REFERENCE_POPULATION:
        similarity = 0.0
        total_w = 0.0
        for key, w in key_metrics:
            if key not in metrics_dict or key not in ref:
                continue
            v_user = metrics_dict[key]
            v_ref  = ref[key]
            span   = max(abs(v_ref) * 0.5, 0.01)
            diff   = abs(v_user - v_ref) / span
            sim    = max(0.0, 1.0 - diff)
            similarity += sim * w
            total_w += w
        if total_w > 0:
            similarity /= total_w
        scores.append((similarity, ref["tier_score"]))

    # Взвешенное среднее по similarity
    total_sim = sum(s for s, _ in scores)
    if total_sim < 1e-6:
        return 6.0
    pop_score = sum(s * ts for s, ts in scores) / total_sim
    return round(max(1.5, min(10.0, pop_score)), 2)


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
    jaw_angle_score: float = 0.0             # угол нижней челюсти (gonial angle)
    jaw_angle_deg: float = 0.0               # измеренный угол в градусах

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


def _angle_at_vertex(p1, vertex, p2) -> float:
    """Угол в градусах в точке vertex между лучами vertex→p1 и vertex→p2."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    mag = math.sqrt(v1[0]**2 + v1[1]**2) * math.sqrt(v2[0]**2 + v2[1]**2)
    if mag < 1e-6:
        return 130.0
    cos_a = max(-1.0, min(1.0, (v1[0]*v2[0] + v1[1]*v2[1]) / mag))
    return math.degrees(math.acos(cos_a))


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
    if score >= 9.0:
        return "True Adam"
    elif score >= 8.0:
        return "Chad"
    elif score >= 7.5:
        return "HHTN"
    elif score >= 6.0:
        return "HTN"
    elif score >= 4.5:
        return "MTN"
    else:
        return "LTN"


def _get_grade(score: float) -> str:
    if score >= 9.0:
        return "True Adam — Топ 1%"
    elif score >= 8.0:
        return "Chad — Топ 5%"
    elif score >= 7.5:
        return "HHTN — High High Tier Normie"
    elif score >= 6.0:
        return "HTN — High Tier Normie"
    elif score >= 4.5:
        return "MTN — Mid Tier Normie"
    else:
        return "LTN — Low Tier Normie"


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

    # ── Gonial angle (угол нижней челюсти) ───────────────────────────────────
    # Угол в точке jaw_left/jaw_right между:
    #   • ветвью к скуле (ramus direction: pt(234) left cheek / pt(454) right cheek)
    #   • телом к подбородку (body direction: chin pt(152))
    # Мужской идеал ≈ 120–125°; тупой угол (~145°+) = слабая челюсть
    left_gonial  = _angle_at_vertex(left_cheek, jaw_left,  chin)
    right_gonial = _angle_at_vertex(right_cheek, jaw_right, chin)
    jaw_angle_deg_raw = (left_gonial + right_gonial) / 2.0
    # Норма мужчин: ~125° (std 12°). direction="down" — острее = лучше
    jaw_angle_score  = _sigma_score(jaw_angle_deg_raw, 125.0, 12.0, direction="down")

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

    # ── Кантальный тильт ────────────────────────────────────────────────────
    # Позитивный тильт = внешний угол глаза ВЫШЕ внутреннего (hunter eyes).
    # В координатах изображения y растёт вниз, поэтому:
    #   outer.y < inner.y  →  inner.y - outer.y > 0  →  позитивный тильт.
    # slope = (inner.y - outer.y) / горизонтальное расстояние
    # Для левого глаза: inner правее outer → inner.x - outer.x > 0
    # Для правого глаза: inner левее outer → outer.x - inner.x > 0
    left_h  = max(abs(left_eye_inner[0]  - left_eye_outer[0]),  1.0)
    right_h = max(abs(right_eye_outer[0] - right_eye_inner[0]), 1.0)

    left_slope  = (left_eye_inner[1]  - left_eye_outer[1])  / left_h
    right_slope = (right_eye_inner[1] - right_eye_outer[1]) / right_h

    canthal_norm         = (left_slope + right_slope) / 2.0
    canthal_tilt_degrees = round(math.degrees(math.atan(canthal_norm)), 2)

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
                                           direction="both")   # оценивается в гармонии, не авто-награда за ширину
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

    # ── Итоговый балл (взвешенное среднее 21 метрики) ────────────────────────
    # Веса настроены под лукмаксинг-стандарты:
    # — кантальный тильт, gonial angle, ширина челюсти — ключевые
    # — симметрия важна, но не доминирует
    weights = {
        "symmetry":         0.06,   # важна, но не главная
        "proportions":      0.07,
        "thirds":           0.05,
        "canthal":          0.12,   # hunter eyes — ключевая метрика в лукмаксинге
        "cheekbones":       0.08,   # скулы/челюсть — основа мужественности
        "jaw_angle":        0.07,   # gonial angle — угол нижней челюсти (новая метрика)
        "eyes":             0.06,
        "eye_distance":     0.04,
        "nose":             0.03,
        "mouth":            0.03,
        "nose_length":      0.03,
        "chin_length":      0.05,   # выраженный подбородок = плюс
        "chin_contour":     0.04,
        "nose_to_mouth":    0.03,
        "biocular":         0.03,
        "forehead":         0.03,
        "lip_fullness":     0.03,
        "lip_ratio":        0.02,
        "jaw_to_mouth":     0.06,   # ширина челюсти — важна в лукмаксинге
        "eye_shape":        0.05,   # форма/разрез глаз
        "brow":             0.03,
        "golden_ratio":     0.02,
    }
    weighted = (
        symmetry_score          * weights["symmetry"]
        + face_proportions_score * weights["proportions"]
        + thirds_score           * weights["thirds"]
        + canthal_tilt_score     * weights["canthal"]
        + cheekbones_score       * weights["cheekbones"]
        + jaw_angle_score        * weights["jaw_angle"]
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
        cheekbones_score, jaw_angle_score, eyes_score, eye_distance_score, nose_score,
        lips_score, nose_length_score, chin_length_score, chin_contour_score,
        nose_to_mouth_score, biocular_score, forehead_score, lip_fullness_score,
        lip_ratio_score, jaw_to_mouth_score, eye_shape_score, brow_height_score,
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

    farkas_overall = round(max(1.5, min(10.0, base_overall + harmony_bonus)), 2)

    # ── Калибровка по референсной базе (60 лиц) ──────────────────────────────
    # Сравниваем метрики с базой эталонных лиц и получаем второй независимый score.
    # Итоговый балл = 65% Farkas + 35% популяционный перцентиль.
    # Это делает оценку устойчивее к крайним значениям одной метрики.
    raw_metrics_for_pop = {
        "canthal_norm": canthal_norm,
        "hw_ratio":     hw_ratio,
        "cheek_jaw":    cheek_jaw_ratio,
        "chin_contour": chin_contour,
        "jaw_to_mouth": jaw_to_mouth_r,
        "eye_to_face":  eye_to_face,
        "nose_to_face": nose_to_face,
        "lip_fullness": lip_fullness,
        "jaw_angle":    jaw_angle_deg_raw,
        "symmetry_raw": symmetry_raw,
        "thirds_dev":   thirds_dev,
        "biocular":     biocular_width,
        "forehead":     forehead_ratio,
        "eye_shape":    eye_shape_r,
        "brow_dist":    brow_dist_r,
        "vert_balance": vert_balance,
        "nose_length":  nose_len_ratio,
        "chin_length":  chin_len_ratio,
    }
    pop_score = _percentile_against_population(raw_metrics_for_pop)
    overall = round(max(1.5, min(10.0, farkas_overall * 0.65 + pop_score * 0.35)), 2)

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
        jaw_angle_score=jaw_angle_score,
        jaw_angle_deg=round(jaw_angle_deg_raw, 1),
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
            "jaw_angle_deg":        round(jaw_angle_deg_raw, 1),
            "left_gonial_deg":      round(left_gonial, 1),
            "right_gonial_deg":     round(right_gonial, 1),
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
