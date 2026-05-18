"""
Тест системы оценки лиц без MediaPipe.
Показывает, почему "идеальное" лицо по Фаркасу получает 7.0 (это и есть норма),
и как выглядят экстремальные случаи.
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from face_analyzer import _sigma_score, _golden_ratio_score, _get_grade, _get_tier, FARKAS

GOLDEN_RATIO = 1.618033988749895


def compute_overall(metrics: dict) -> tuple[float, str, str, list]:
    """Вычисляет итоговый балл по всем метрикам (та же логика, что в analyze_face)."""

    hw_ratio         = metrics["hw_ratio"]
    vert_balance     = metrics["vert_balance"]
    cheek_jaw_ratio  = metrics["cheek_jaw_ratio"]
    canthal_norm     = metrics["canthal_norm"]
    eye_to_face      = metrics["eye_to_face"]
    inner_eye_to_face = metrics["inner_eye_to_face"]
    nose_to_face     = metrics["nose_to_face"]
    mouth_to_face    = metrics["mouth_to_face"]
    nose_len_ratio   = metrics["nose_len_ratio"]
    chin_len_ratio   = metrics["chin_len_ratio"]
    chin_contour     = metrics["chin_contour"]
    nose_to_mouth    = metrics["nose_to_mouth"]
    biocular_width   = metrics["biocular_width"]
    forehead_ratio   = metrics["forehead_ratio"]
    lip_fullness     = metrics["lip_fullness"]
    lip_ratio        = metrics["lip_ratio"]
    jaw_to_mouth_r   = metrics["jaw_to_mouth_r"]
    eye_shape_r      = metrics["eye_shape_r"]
    brow_dist_r      = metrics["brow_dist_r"]
    jaw_angle_deg    = metrics["jaw_angle_deg"]
    symmetry_raw     = metrics["symmetry_raw"]
    thirds_dev       = metrics["thirds_dev"]

    face_height = metrics["face_height"]
    face_width  = metrics["face_width"]

    golden_ratio_score      = _golden_ratio_score(face_height, face_width)
    face_proportions_score  = _sigma_score(hw_ratio,           *FARKAS["face_hw_ratio"],    direction="up")
    vertical_balance_score  = _sigma_score(vert_balance,       *FARKAS["vertical_balance"],  direction="down")
    cheekbones_score        = _sigma_score(cheek_jaw_ratio,    *FARKAS["cheek_jaw"],         direction="down")
    canthal_tilt_score      = _sigma_score(canthal_norm,       *FARKAS["canthal_tilt"],      direction="up")
    eyes_score              = _sigma_score(eye_to_face,        *FARKAS["eye_to_face"])
    eye_distance_score      = _sigma_score(inner_eye_to_face,  *FARKAS["inner_eye_to_face"])
    nose_score              = _sigma_score(nose_to_face,       *FARKAS["nose_to_face"],      direction="down")
    lips_score              = _sigma_score(mouth_to_face,      *FARKAS["mouth_to_face"])
    nose_length_score       = _sigma_score(nose_len_ratio,     *FARKAS["nose_length"])
    chin_length_score       = _sigma_score(chin_len_ratio,     *FARKAS["chin_length"],       direction="up")
    chin_contour_score      = _sigma_score(chin_contour,       *FARKAS["chin_contour"],      direction="down")
    nose_to_mouth_score     = _sigma_score(nose_to_mouth,      *FARKAS["nose_to_mouth"])
    biocular_score          = _sigma_score(biocular_width,     *FARKAS["biocular_width"])
    forehead_score          = _sigma_score(forehead_ratio,     *FARKAS["forehead_width"])
    lip_fullness_score      = _sigma_score(lip_fullness,       *FARKAS["lip_fullness"],      direction="up")
    lip_ratio_score         = _sigma_score(lip_ratio,          *FARKAS["lip_ratio"])
    jaw_to_mouth_score      = _sigma_score(jaw_to_mouth_r,     *FARKAS["jaw_to_mouth"],      direction="up")
    eye_shape_score         = _sigma_score(eye_shape_r,        *FARKAS["eye_shape"])
    brow_height_score       = _sigma_score(brow_dist_r,        *FARKAS["brow_height"],       direction="down")
    jaw_angle_score         = _sigma_score(jaw_angle_deg,      125.0, 12.0,                  direction="down")

    symmetry_score = round(max(2.0, min(10.0, symmetry_raw * 10.0 + 0.5)), 2)
    thirds_score   = round(max(3.5, 9.5 - thirds_dev * 30.0), 2)

    scores = {
        "symmetry":         symmetry_score,
        "proportions":      face_proportions_score,
        "thirds":           thirds_score,
        "canthal":          canthal_tilt_score,
        "cheekbones":       cheekbones_score,
        "jaw_angle":        jaw_angle_score,
        "eyes":             eyes_score,
        "eye_distance":     eye_distance_score,
        "nose":             nose_score,
        "mouth":            lips_score,
        "nose_length":      nose_length_score,
        "chin_length":      chin_length_score,
        "chin_contour":     chin_contour_score,
        "nose_to_mouth":    nose_to_mouth_score,
        "biocular":         biocular_score,
        "forehead":         forehead_score,
        "lip_fullness":     lip_fullness_score,
        "lip_ratio":        lip_ratio_score,
        "jaw_to_mouth":     jaw_to_mouth_score,
        "eye_shape":        eye_shape_score,
        "brow":             brow_height_score,
        "golden_ratio":     golden_ratio_score,
    }

    weights = {
        "symmetry":      0.06,
        "proportions":   0.07,
        "thirds":        0.05,
        "canthal":       0.12,
        "cheekbones":    0.08,
        "jaw_angle":     0.07,
        "eyes":          0.06,
        "eye_distance":  0.04,
        "nose":          0.03,
        "mouth":         0.03,
        "nose_length":   0.03,
        "chin_length":   0.05,
        "chin_contour":  0.04,
        "nose_to_mouth": 0.03,
        "biocular":      0.03,
        "forehead":      0.03,
        "lip_fullness":  0.03,
        "lip_ratio":     0.02,
        "jaw_to_mouth":  0.06,
        "eye_shape":     0.05,
        "brow":          0.03,
        "golden_ratio":  0.02,
    }

    weighted = sum(scores[k] * weights[k] for k in weights)
    weight_total = sum(weights.values())
    base_overall = weighted / weight_total

    all_metric_scores = list(scores.values())
    above_norm = sum(1 for s in all_metric_scores if s >= 7.0)
    harmony_bonus = 0.0
    if above_norm >= 10: harmony_bonus = 0.25
    if above_norm >= 13: harmony_bonus = 0.50
    if above_norm >= 16: harmony_bonus = 0.80

    if symmetry_score >= 8.0 and face_proportions_score >= 8.0:
        harmony_bonus += 0.20
    if canthal_tilt_score >= 8.0 and cheekbones_score >= 7.5:
        harmony_bonus += 0.15
    if jaw_to_mouth_score >= 7.5 and chin_length_score >= 7.5:
        harmony_bonus += 0.10

    overall = round(max(1.5, min(10.0, base_overall + harmony_bonus)), 2)
    return overall, _get_grade(overall), _get_tier(overall), scores


def print_report(name: str, metrics: dict):
    overall, grade, tier, scores = compute_overall(metrics)
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  ИТОГ: {overall:.2f}/10  |  {tier}  |  {grade}")
    print(f"  Метрик выше нормы (≥7.0): {sum(1 for s in scores.values() if s >= 7.0)}/22")
    print(f"\n  Детали по метрикам:")

    name_map = {
        "symmetry":      "Симметрия         (вес 6%)",
        "proportions":   "Пропорции H/W     (вес 7%)",
        "thirds":        "Трети лица        (вес 5%)",
        "canthal":       "Кантальный тильт  (вес 12%)",
        "cheekbones":    "Скулы/Челюсть     (вес 8%)",
        "jaw_angle":     "Gonial угол       (вес 7%)",
        "eyes":          "Размер глаз       (вес 6%)",
        "eye_distance":  "Расст. между глаз (вес 4%)",
        "nose":          "Ширина носа       (вес 3%)",
        "mouth":         "Ширина рта        (вес 3%)",
        "nose_length":   "Длина носа        (вес 3%)",
        "chin_length":   "Длина подбородка  (вес 5%)",
        "chin_contour":  "Контур подборд.   (вес 4%)",
        "nose_to_mouth": "Нос/рот           (вес 3%)",
        "biocular":      "Биокулярная шир.  (вес 3%)",
        "forehead":      "Ширина лба        (вес 3%)",
        "lip_fullness":  "Полнота губ       (вес 3%)",
        "lip_ratio":     "Пропорции губ     (вес 2%)",
        "jaw_to_mouth":  "Челюсть/рот       (вес 6%)",
        "eye_shape":     "Форма глаз        (вес 5%)",
        "brow":          "Высота брови      (вес 3%)",
        "golden_ratio":  "Золотое сечение   (вес 2%)",
    }

    for key, score in scores.items():
        bar = "█" * int(score) + "░" * (10 - int(score))
        label = name_map.get(key, key)
        flag = " ← НИЗКИЙ!" if score < 6.0 else (" ← ЭЛИТА" if score >= 9.0 else "")
        print(f"  {label}: {bar} {score:.1f}{flag}")


# ─────────────────────────────────────────────────────────────────────────────
# ЛИЦО 1: "Идеальное" по Фаркасу (ровно средние значения нормы)
# → Получит 7.0 — потому что 7.0 И ЕСТЬ "нормальное/среднее" лицо по алгоритму
# ─────────────────────────────────────────────────────────────────────────────
face_farkas_norm = {
    "hw_ratio":         FARKAS["face_hw_ratio"][0],       # = 0.896
    "vert_balance":     FARKAS["vertical_balance"][0],    # = 0.728
    "cheek_jaw_ratio":  FARKAS["cheek_jaw"][0],           # = 1.356
    "canthal_norm":     FARKAS["canthal_tilt"][0],        # = 0.036
    "eye_to_face":      FARKAS["eye_to_face"][0],         # = 0.223
    "inner_eye_to_face":FARKAS["inner_eye_to_face"][0],   # = 0.271
    "nose_to_face":     FARKAS["nose_to_face"][0],        # = 0.234
    "mouth_to_face":    FARKAS["mouth_to_face"][0],       # = 0.403
    "nose_len_ratio":   FARKAS["nose_length"][0],         # = 0.421
    "chin_len_ratio":   FARKAS["chin_length"][0],         # = 0.283
    "chin_contour":     FARKAS["chin_contour"][0],        # = 0.630
    "nose_to_mouth":    FARKAS["nose_to_mouth"][0],       # = 0.583
    "biocular_width":   FARKAS["biocular_width"][0],      # = 0.713
    "forehead_ratio":   FARKAS["forehead_width"][0],      # = 0.919
    "lip_fullness":     FARKAS["lip_fullness"][0],        # = 0.347
    "lip_ratio":        FARKAS["lip_ratio"][0],           # = 0.639
    "jaw_to_mouth_r":   FARKAS["jaw_to_mouth"][0],        # = 1.810
    "eye_shape_r":      FARKAS["eye_shape"][0],           # = 0.285
    "brow_dist_r":      FARKAS["brow_height"][0],         # = 0.063
    "jaw_angle_deg":    125.0,
    "symmetry_raw":     0.95,     # идеальная симметрия
    "thirds_dev":       0.0,      # идеальные трети
    "face_height":      896.0,
    "face_width":       1000.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# ЛИЦО 2: "Лукмаксинг-элита" (2+ σ в нужную сторону по ключевым метрикам)
# ─────────────────────────────────────────────────────────────────────────────
def farkas_sigma(key, sigma, direction="up"):
    mean, std = FARKAS[key]
    if direction == "up":
        return mean + sigma * std
    else:
        return mean - sigma * std

face_elite = {
    "hw_ratio":          farkas_sigma("face_hw_ratio",    2.5, "up"),    # длиннее лицо
    "vert_balance":      farkas_sigma("vertical_balance", 2.5, "down"),  # длиннее нижняя треть
    "cheek_jaw_ratio":   farkas_sigma("cheek_jaw",        2.5, "down"),  # шире челюсть
    "canthal_norm":      farkas_sigma("canthal_tilt",     2.5, "up"),    # сильный hunter eyes
    "eye_to_face":       FARKAS["eye_to_face"][0],
    "inner_eye_to_face": FARKAS["inner_eye_to_face"][0],
    "nose_to_face":      farkas_sigma("nose_to_face",     2.0, "down"),  # уже нос
    "mouth_to_face":     FARKAS["mouth_to_face"][0],
    "nose_len_ratio":    FARKAS["nose_length"][0],
    "chin_len_ratio":    farkas_sigma("chin_length",      2.5, "up"),    # длиннее подбородок
    "chin_contour":      farkas_sigma("chin_contour",     2.0, "down"),  # V-образный
    "nose_to_mouth":     FARKAS["nose_to_mouth"][0],
    "biocular_width":    FARKAS["biocular_width"][0],
    "forehead_ratio":    FARKAS["forehead_width"][0],
    "lip_fullness":      farkas_sigma("lip_fullness",     1.5, "up"),
    "lip_ratio":         FARKAS["lip_ratio"][0],
    "jaw_to_mouth_r":    farkas_sigma("jaw_to_mouth",     2.5, "up"),    # широкая челюсть vs рот
    "eye_shape_r":       FARKAS["eye_shape"][0],
    "brow_dist_r":       farkas_sigma("brow_height",      2.0, "down"),  # низкие брови
    "jaw_angle_deg":     105.0,    # острый gonial — очень мужественный
    "symmetry_raw":      0.985,
    "thirds_dev":        0.0,
    "face_height":       896.0,
    "face_width":        1000.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# ЛИЦО 3: "Уродливое" (2+ σ в плохую сторону по всем метрикам)
# ─────────────────────────────────────────────────────────────────────────────
face_ugly = {
    "hw_ratio":          farkas_sigma("face_hw_ratio",    2.5, "down"),  # слишком круглое
    "vert_balance":      farkas_sigma("vertical_balance", 2.5, "up"),    # большая средняя треть
    "cheek_jaw_ratio":   farkas_sigma("cheek_jaw",        2.5, "up"),    # узкая челюсть
    "canthal_norm":      -0.12,                                           # негативный тильт (опущен уголок)
    "eye_to_face":       farkas_sigma("eye_to_face",      2.5, "up"),    # слишком большие или маленькие
    "inner_eye_to_face": farkas_sigma("inner_eye_to_face",2.5, "up"),    # широко расставленные
    "nose_to_face":      farkas_sigma("nose_to_face",     2.5, "up"),    # широкий нос
    "mouth_to_face":     farkas_sigma("mouth_to_face",    2.5, "up"),    # очень широкий рот
    "nose_len_ratio":    farkas_sigma("nose_length",      2.5, "up"),    # длинный нос
    "chin_len_ratio":    farkas_sigma("chin_length",      2.5, "down"),  # слабый подбородок
    "chin_contour":      farkas_sigma("chin_contour",     2.5, "up"),    # квадратный подбородок
    "nose_to_mouth":     farkas_sigma("nose_to_mouth",    2.5, "up"),    # нос шире рта
    "biocular_width":    farkas_sigma("biocular_width",   2.5, "up"),    # очень широкий
    "forehead_ratio":    farkas_sigma("forehead_width",   2.5, "up"),    # выпуклый лоб
    "lip_fullness":      farkas_sigma("lip_fullness",     2.5, "down"),  # тонкие губы
    "lip_ratio":         farkas_sigma("lip_ratio",        2.5, "up"),    # нарушенные пропорции губ
    "jaw_to_mouth_r":    farkas_sigma("jaw_to_mouth",     2.5, "down"),  # узкая челюсть vs рот
    "eye_shape_r":       farkas_sigma("eye_shape",        2.5, "up"),    # нарушенная форма
    "brow_dist_r":       farkas_sigma("brow_height",      2.5, "up"),    # высокие брови
    "jaw_angle_deg":     155.0,    # очень тупой gonial — слабая, «мягкая» челюсть
    "symmetry_raw":      0.70,     # выраженная асимметрия
    "thirds_dev":        0.25,     # трети очень несбалансированны
    "face_height":       820.0,
    "face_width":        1000.0,
}


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  АНАЛИЗ СИСТЕМЫ ОЦЕНКИ ЛИЦ")
    print("  Проверка без MediaPipe (прямой расчёт метрик)")
    print("="*60)

    print("\n>> ОБЪЯСНЕНИЕ: Почему 'идеальное' лицо получает 7?")
    print("   Алгоритм построен так, что значения Farkas norm (среднее")
    print("   по реальным людям) дают ровно 7.0 — это нормальное лицо.")
    print("   Чтобы получить 10, нужно быть на 2+ σ выше нормы по")
    print("   ключевым метрикам (hunter eyes, chelюсть, gonial угол).")

    print_report("ЛИЦО А: Фаркас-норма (среднее значение = 7.0 по дизайну)", face_farkas_norm)
    print_report("ЛИЦО Б: Лукмаксинг-элита (+2.5σ по ключевым метрикам)", face_elite)
    print_report("ЛИЦО В: Ужасные пропорции (−2.5σ по всем метрикам)", face_ugly)

    print("\n" + "="*60)
    print("  ИТОГОВАЯ ТАБЛИЦА")
    print("="*60)
    for face_name, face_data in [
        ("А — Farkas норма (ожидалось 10, вышло 7)", face_farkas_norm),
        ("Б — Лукмаксинг-элита",                     face_elite),
        ("В — Ужасное лицо (<3)",                     face_ugly),
    ]:
        overall, grade, tier, _ = compute_overall(face_data)
        print(f"  Лицо {face_name}: {overall:.2f}/10 → {tier}")

    print()
