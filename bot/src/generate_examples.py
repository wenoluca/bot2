"""
Генерирует два примера PDF (краткий и полный разбор)
используя реальное фото из assets/example_face.png.
Запускать из bot/src/:  python generate_examples.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from face_analyzer import FaceMetrics, analyze_face
from pdf_generator import generate_brief_pdf, generate_full_pdf

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# ── Читаем реальное фото и получаем аннотацию ────────────────────────────────
photo_path = os.path.join(ASSETS, "example_face.png")
with open(photo_path, "rb") as f:
    img_bytes = f.read()

real = analyze_face(img_bytes)
annotated_image = real.landmark_image if real else None

# ── Скорректированные метрики для примера ────────────────────────────────────
metrics = FaceMetrics(
    overall_score=8.42,
    grade="S — Высокая привлекательность",
    tier="HTN",
    golden_ratio_score=8.3,
    symmetry_score=9.96,
    facial_thirds_score=9.30,
    canthal_tilt_degrees=6.2,
    canthal_tilt_score=9.98,
    jaw_score=9.22,
    eyes_score=8.15,
    nose_score=9.98,
    lips_score=8.80,
    cheekbones_score=9.22,
    eyebrows_score=7.12,
    balance_score=9.52,
    # Extended 20-metric scores
    face_proportions_score=9.66,
    vertical_balance_score=9.30,
    eye_distance_score=2.00,
    nose_length_score=9.47,
    chin_length_score=9.96,
    chin_contour_score=8.44,
    nose_to_mouth_score=8.49,
    biocular_score=3.73,
    forehead_score=4.96,
    lip_fullness_score=9.99,
    lip_ratio_score=6.79,
    jaw_to_mouth_score=7.79,
    eye_shape_score=9.13,
    brow_height_score=7.12,
    # Raw
    face_width=232.8,
    face_height=289.6,
    upper_third=79.5,
    middle_third=78.2,
    lower_third=81.8,
    left_eye_width=36.1,
    right_eye_width=35.8,
    mouth_width=69.4,
    nose_width=37.2,
    interpupillary_distance=69.8,
    landmark_image=annotated_image,
    details={
        "jaw_to_cheek_ratio":   1.427,
        "ipd_to_face_ratio":    0.300,
        "face_hw_ratio":        0.904,
        "upper_third_pct":      33.2,
        "middle_third_pct":     32.7,
        "lower_third_pct":      34.1,
        "eye_symmetry":         9.96,
        "cheek_symmetry":       9.80,
        "mouth_symmetry":       9.90,
        "cheek_jaw_ratio":      1.427,
        "eye_to_face":          0.155,
        "nose_to_face":         0.223,
        "mouth_to_face":        0.392,
        "inner_eye_to_face":    0.318,
        "biocular_width":       0.752,
        "forehead_ratio":       0.955,
        "nose_len_ratio":       0.411,
        "chin_len_ratio":       0.287,
        "chin_contour":         0.570,
        "nose_to_mouth":        0.570,
        "lip_fullness":         0.345,
        "lip_ratio":            0.576,
        "jaw_to_mouth":         1.788,
        "eye_shape":            0.219,
        "brow_dist_ratio":      0.063,
        "vert_balance":         0.697,
        "canthal_norm":         0.138,
    },
)

os.makedirs(ASSETS, exist_ok=True)

brief_path = os.path.join(ASSETS, "example_brief.pdf")
full_path  = os.path.join(ASSETS, "example_full.pdf")

print("Генерирую краткий разбор...")
with open(brief_path, "wb") as f:
    f.write(generate_brief_pdf(metrics, "пример"))
print(f"  ✓ {brief_path}")

print("Генерирую полный разбор...")
with open(full_path, "wb") as f:
    f.write(generate_full_pdf(metrics, "пример"))
print(f"  ✓ {full_path}")

print("Готово!")
