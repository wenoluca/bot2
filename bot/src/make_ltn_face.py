"""
Создаёт LTN-лицо путём геометрической деформации реального фото:
- очень широкое круглое лицо (hw_ratio << 0.896)
- выраженная асимметрия (один глаз выше другого)
- большой лоб, маленький подбородок (нарушенные трети)
- негативный кантальный тильт (уголки глаз опущены)
"""
import cv2
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
SRC    = os.path.join(ASSETS, "example_face.jpg")
DST    = os.path.join(ASSETS, "ltn_face_warped.png")


def make_ltn_face():
    img = cv2.imread(SRC)
    h, w = img.shape[:2]

    # ── 1. Делаем лицо широким и приплюснутым (умеренно) ────────────────────
    wide_w = int(w * 1.45)
    short_h = int(h * 0.78)
    face_wide = cv2.resize(img, (wide_w, short_h))

    # ── 2. Добавляем большой лоб сверху, убираем часть подбородка снизу ──────
    forehead_pad = int(short_h * 0.35)
    total_h = short_h + forehead_pad
    canvas = np.full((total_h, wide_w, 3), 240, dtype=np.uint8)
    canvas[forehead_pad:forehead_pad + short_h, :] = face_wide
    # Обрезаем нижние 15% — убираем подбородок
    canvas = canvas[:int(total_h * 0.85), :]

    # ── 3. Лёгкая асимметрия: сдвигаем левую половину вниз ──────────────────
    rows, cols = canvas.shape[:2]
    mid   = cols // 2
    shift = int(rows * 0.04)
    left_half = canvas[:, :mid].copy()
    left_shifted = np.full_like(left_half, 240)
    left_shifted[shift:, :] = left_half[:rows - shift, :]
    canvas[:, :mid] = left_shifted

    # ── 4. Финальный ресайз ───────────────────────────────────────────────────
    rows, cols = canvas.shape[:2]
    final = cv2.resize(canvas, (768, 768))

    cv2.imwrite(DST, final)
    print(f"Сохранено: {DST}")
    return DST


if __name__ == "__main__":
    out = make_ltn_face()

    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from face_analyzer import analyze_face

    with open(out, "rb") as f:
        img_bytes = f.read()

    print("Анализирую деформированное лицо...")
    m = analyze_face(img_bytes)
    if m:
        print(f"\n{'='*40}")
        print(f"ИТОГ: {m.overall_score}/10 → {m.tier}")
        print(f"Grade: {m.grade}")
        print(f"{'='*40}")
        print(f"Симметрия:        {m.symmetry_score}")
        print(f"Пропорции H/W:    {m.face_proportions_score}")
        print(f"Трети:            {m.facial_thirds_score}")
        print(f"Кантальный тильт: {m.canthal_tilt_score} ({m.canthal_tilt_degrees}°)")
        print(f"Скулы/Челюсть:    {m.cheekbones_score}")
        print(f"Gonial угол:      {m.jaw_angle_deg:.1f}°")
        print(f"Глаза:            {m.eyes_score}")
        print(f"Нос:              {m.nose_score}")
        print(f"Face: {m.face_width:.0f}x{m.face_height:.0f}")
    else:
        print("ЛИЦО НЕ НАЙДЕНО — MediaPipe не смог детектировать")
