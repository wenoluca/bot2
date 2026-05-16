"""
Генерирует два примера PDF (краткий и полный разбор)
с данными искусственного привлекательного мужского лица.
Запускать из bot/src/:  python generate_examples.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from face_analyzer import FaceMetrics
from pdf_generator import generate_brief_pdf, generate_full_pdf

# ── Пример: Алекс, 25 лет, привлекательный мужчина ─────────────────────────
metrics = FaceMetrics(
    overall_score=8.3,
    grade="A+ — Выше среднего",
    tier="HTN",
    golden_ratio_score=8.6,
    symmetry_score=8.8,
    facial_thirds_score=8.1,
    canthal_tilt_degrees=5.8,
    canthal_tilt_score=9.0,
    jaw_score=8.1,
    eyes_score=8.6,
    nose_score=7.9,
    lips_score=8.3,
    cheekbones_score=8.5,
    eyebrows_score=7.7,
    balance_score=8.5,
    face_width=188.0,
    face_height=240.0,
    upper_third=79.2,
    middle_third=78.4,
    lower_third=82.4,
    left_eye_width=36.1,
    right_eye_width=35.8,
    mouth_width=69.4,
    nose_width=37.2,
    interpupillary_distance=69.8,
    landmark_image=None,
    details={
        "jaw_to_cheek_ratio": 0.748,
        "ipd_to_face_ratio":  0.371,
        "face_hw_ratio":      1.617,
        "upper_third_pct":    33.1,
        "middle_third_pct":   32.8,
        "lower_third_pct":    34.1,
        "eye_symmetry":       9.1,
        "cheek_symmetry":     8.7,
        "mouth_symmetry":     8.5,
        "cheek_jaw_ratio":    1.337,
    },
)

out_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(out_dir, exist_ok=True)

brief_path = os.path.join(out_dir, "example_brief.pdf")
full_path  = os.path.join(out_dir, "example_full.pdf")

print("Генерирую краткий разбор...")
brief_bytes = generate_brief_pdf(metrics, "alex_example")
with open(brief_path, "wb") as f:
    f.write(brief_bytes)
print(f"  ✓ {brief_path}  ({len(brief_bytes)//1024} КБ)")

print("Генерирую полный разбор...")
full_bytes = generate_full_pdf(metrics, "alex_example")
with open(full_path, "wb") as f:
    f.write(full_bytes)
print(f"  ✓ {full_path}  ({len(full_bytes)//1024} КБ)")

print("Готово!")
