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

# ── Скорректированные метрики (фото не строго анфас — исправляем отклонения) ─
metrics = FaceMetrics(
    overall_score=8.5,
    grade="S — Высокая привлекательность",
    tier="HTN",
    golden_ratio_score=8.3,
    symmetry_score=9.2,
    facial_thirds_score=8.0,
    canthal_tilt_degrees=4.5,
    canthal_tilt_score=8.5,
    jaw_score=8.8,
    eyes_score=8.5,
    nose_score=7.6,
    lips_score=7.8,
    cheekbones_score=9.3,
    eyebrows_score=8.2,
    balance_score=8.5,
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
        "jaw_to_cheek_ratio":  0.748,
        "ipd_to_face_ratio":   0.371,
        "face_hw_ratio":       1.614,
        "upper_third_pct":     33.2,
        "middle_third_pct":    32.7,
        "lower_third_pct":     34.1,
        "eye_symmetry":        9.48,
        "cheek_symmetry":      8.97,
        "mouth_symmetry":      9.12,
        "cheek_jaw_ratio":     1.337,
    },
)

os.makedirs(ASSETS, exist_ok=True)

brief_path = os.path.join(ASSETS, "example_brief.pdf")
full_path  = os.path.join(ASSETS, "example_full.pdf")

print("Генерирую краткий разбор...")
with open(brief_path, "wb") as f:
    f.write(generate_brief_pdf(metrics, "alex_example"))
print(f"  ✓ {brief_path}")

print("Генерирую полный разбор...")
with open(full_path, "wb") as f:
    f.write(generate_full_pdf(metrics, "alex_example"))
print(f"  ✓ {full_path}")

print("Готово!")
