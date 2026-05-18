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
photo_path = os.path.join(ASSETS, "example_face.jpg")
with open(photo_path, "rb") as f:
    img_bytes = f.read()

# Конвертируем в JPEG для landmark_image (как в боте)
pil = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
jpg_buf = io.BytesIO()
pil.save(jpg_buf, format="JPEG", quality=92)
photo_jpeg = jpg_buf.getvalue()

# ── Реальный анализ фото ───────────────────────────────────────────────────────
from face_analyzer import analyze_face

print("Запускаю реальный анализ фото...")
metrics = analyze_face(img_bytes)
if metrics is None:
    raise RuntimeError("Лицо не найдено в example_face.jpg")

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
