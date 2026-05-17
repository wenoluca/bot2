"""
Генерирует два примера PDF (краткий и полный разбор)
используя реальное фото из assets/example_face.png.
Запускать из bot/src/:  python generate_examples.py
"""
import io
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from face_analyzer import FaceMetrics
from pdf_generator import generate_brief_pdf, generate_full_pdf
from PIL import Image as PILImage

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# ── Читаем фото примера ───────────────────────────────────────────────────────
photo_path = os.path.join(ASSETS, "example_face.png")
with open(photo_path, "rb") as f:
    img_bytes = f.read()

# Конвертируем в JPEG для landmark_image (как в боте)
pil = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
jpg_buf = io.BytesIO()
pil.save(jpg_buf, format="JPEG", quality=92)
photo_jpeg = jpg_buf.getvalue()

# ── Метрики примера (высокая привлекательность — мужское лицо) ───────────────
metrics = FaceMetrics(
    overall_score=8.74,
    grade="S — Высокая привлекательность",
    tier="HTN",
    golden_ratio_score=8.9,
    symmetry_score=9.61,
    facial_thirds_score=9.10,
    canthal_tilt_degrees=7.4,
    canthal_tilt_score=9.85,
    jaw_score=9.40,
    eyes_score=8.30,
    nose_score=9.71,
    lips_score=8.55,
    cheekbones_score=9.40,
    eyebrows_score=8.20,
    balance_score=9.20,
    # Extended 20-metric scores
    face_proportions_score=9.44,
    vertical_balance_score=9.10,
    eye_distance_score=7.80,
    nose_length_score=9.20,
    chin_length_score=9.71,
    chin_contour_score=8.90,
    nose_to_mouth_score=8.60,
    biocular_score=8.10,
    forehead_score=8.50,
    lip_fullness_score=9.30,
    lip_ratio_score=7.90,
    jaw_to_mouth_score=9.10,
    eye_shape_score=9.40,
    brow_height_score=8.20,
    # Raw measurements
    face_width=238.4,
    face_height=295.2,
    upper_third=80.1,
    middle_third=79.8,
    lower_third=82.3,
    left_eye_width=37.2,
    right_eye_width=36.9,
    mouth_width=71.0,
    nose_width=38.1,
    interpupillary_distance=71.4,
    landmark_image=photo_jpeg,
    details={
        "jaw_to_cheek_ratio":   1.440,
        "ipd_to_face_ratio":    0.300,
        "face_hw_ratio":        0.907,
        "upper_third_pct":      33.0,
        "middle_third_pct":     32.9,
        "lower_third_pct":      34.1,
        "eye_symmetry":         9.61,
        "cheek_symmetry":       9.75,
        "mouth_symmetry":       9.80,
        "cheek_jaw_ratio":      1.440,
        "eye_to_face":          0.220,
        "nose_to_face":         0.234,
        "mouth_to_face":        0.398,
        "inner_eye_to_face":    0.285,
        "biocular_width":       0.720,
        "forehead_ratio":       0.930,
        "nose_len_ratio":       0.416,
        "chin_len_ratio":       0.284,
        "chin_contour":         0.620,
        "nose_to_mouth":        0.572,
        "lip_fullness":         0.342,
        "lip_ratio":            0.621,
        "jaw_to_mouth":         1.791,
        "eye_shape":            0.244,
        "brow_dist_ratio":      0.065,
        "vert_balance":         0.710,
        "canthal_norm":         0.148,
    },
)

os.makedirs(ASSETS, exist_ok=True)

brief_path = os.path.join(ASSETS, "example_brief.pdf")
full_path  = os.path.join(ASSETS, "example_full.pdf")

print("Генерирую краткий разбор...")
with open(brief_path, "wb") as f:
    f.write(generate_brief_pdf(metrics, "пример"))
print(f"  OK {brief_path}")

print("Генерирую полный разбор...")
with open(full_path, "wb") as f:
    f.write(generate_full_pdf(metrics, "пример"))
print(f"  OK {full_path}")

print("Готово!")
