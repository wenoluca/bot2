"""
Generates instruction images for the bot showing correct/incorrect photo poses.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH  = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")

BG       = (18, 18, 30)
GREEN    = (72, 199, 142)
RED      = (255, 82, 82)
WHITE    = (240, 240, 255)
GREY     = (140, 140, 160)
YELLOW   = (255, 200, 60)

W, H = 800, 520


def _font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _draw_face_oval(draw, cx, cy, rw, rh, color, width=4):
    draw.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], outline=color, width=width)


def _draw_eyes(draw, cx, cy, rw, rh, color, tilt_deg=0):
    ey = cy - rh * 0.15
    ex_l = cx - rw * 0.38
    ex_r = cx + rw * 0.38
    ew, eh = rw * 0.18, rh * 0.07

    for ex in (ex_l, ex_r):
        draw.ellipse([ex - ew, ey - eh, ex + ew, ey + eh], fill=color)
        draw.ellipse([ex - ew * 0.5, ey - eh * 0.5, ex + ew * 0.5, ey + eh * 0.5],
                     fill=BG)


def _draw_nose(draw, cx, cy, rw, rh, color):
    ny_top = cy + rh * 0.05
    ny_bot = cy + rh * 0.38
    nw     = rw * 0.14
    draw.line([(cx, ny_top), (cx, ny_bot)], fill=color, width=3)
    draw.line([(cx, ny_bot), (cx - nw, ny_bot + rh * 0.06)], fill=color, width=3)
    draw.line([(cx, ny_bot), (cx + nw, ny_bot + rh * 0.06)], fill=color, width=3)


def _draw_mouth(draw, cx, cy, rh, color):
    my = cy + rh * 0.55
    mw = 25
    draw.arc([cx - mw, my - 10, cx + mw, my + 10], 0, 180, fill=color, width=3)


def _draw_face_frontal(draw, cx, cy, color):
    rw, rh = 80, 105
    _draw_face_oval(draw, cx, cy, rw, rh, color)
    _draw_eyes(draw, cx, cy, rw, rh, color)
    _draw_nose(draw, cx, cy, rw, rh, color)
    _draw_mouth(draw, cx, cy, rh, color)
    # hair
    draw.arc([cx - rw, cy - rh, cx + rw, cy - rh + 40], 200, 340, fill=GREY, width=5)


def _draw_face_profile(draw, cx, cy, color):
    """Side profile - face turned 90 degrees."""
    rw, rh = 55, 100
    # head - offset to simulate profile
    draw.ellipse([cx - 20, cy - rh, cx + rw + 30, cy + rh], outline=color, width=4)
    # One eye only
    ey = cy - rh * 0.15
    draw.ellipse([cx + 20, ey - 8, cx + 55, ey + 8], fill=color)
    draw.ellipse([cx + 28, ey - 4, cx + 47, ey + 4], fill=BG)
    # Profile nose bump
    draw.line([(cx + rw + 28, cy - 10), (cx + rw + 48, cy + 20),
               (cx + rw + 32, cy + 32)], fill=color, width=4)
    # Lips
    draw.arc([cx + rw - 5, cy + 40, cx + rw + 30, cy + 70], 270, 360, fill=color, width=3)
    # Chin curve
    draw.arc([cx - 20, cy + rh - 30, cx + 60, cy + rh + 20], 0, 70, fill=color, width=4)


def _draw_face_tilted(draw, cx, cy, color):
    """Face tilted to the shoulder."""
    angle = math.radians(22)
    rw, rh = 80, 105

    def rot(px, py):
        px -= cx; py -= cy
        rx = px * math.cos(angle) - py * math.sin(angle)
        ry = px * math.sin(angle) + py * math.cos(angle)
        return rx + cx, ry + cy

    # Head oval via polygon
    pts = []
    for i in range(0, 360, 4):
        r = math.radians(i)
        x = cx + rw * math.cos(r)
        y = cy + rh * math.sin(r)
        pts.append(rot(x, y))
    draw.polygon(pts, outline=color, fill=None)

    # Eyes
    ey = cy - rh * 0.15
    for ex in (cx - rw * 0.38, cx + rw * 0.38):
        ew, eh = rw * 0.18, rh * 0.07
        corners = [(ex - ew, ey - eh), (ex + ew, ey - eh),
                   (ex + ew, ey + eh), (ex - ew, ey + eh)]
        rotated = [rot(px, py) for px, py in corners]
        draw.polygon(rotated, fill=color)

    # Nose
    nose_pts = [(cx, cy + rh * 0.05), (cx, cy + rh * 0.38),
                (cx - rw * 0.14, cy + rh * 0.44), (cx, cy + rh * 0.38),
                (cx + rw * 0.14, cy + rh * 0.44)]
    for i in range(0, len(nose_pts) - 1):
        p1 = rot(*nose_pts[i])
        p2 = rot(*nose_pts[i + 1])
        draw.line([p1, p2], fill=color, width=3)

    # Tilt angle indicator arrow
    ax, ay = cx + rw + 30, cy
    draw.line([(ax, ay - 40), (ax, ay + 40)], fill=YELLOW, width=2)
    draw.polygon([(ax - 8, ay - 30), (ax + 8, ay - 30), (ax, ay - 48)], fill=YELLOW)
    draw.line([(ax - 15, ay - 10), (ax + 15, ay + 30)], fill=RED, width=3)


def _badge(draw, img, x, y, text, color):
    fw = _font(22)
    bbox = draw.textbbox((0, 0), text, font=fw)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = 12
    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + th + pad],
                            radius=8, fill=color)
    draw.text((x + pad, y + pad // 2), text, font=fw, fill=BG)


def _divider(draw, x, y1, y2):
    draw.line([(x, y1), (x, y2)], fill=(60, 60, 80), width=2)


def _bullet(draw, x, y, text, color, size=17):
    f = _font(size)
    draw.text((x, y), "• " + text, font=f, fill=color)
    bbox = draw.textbbox((x, y), "• " + text, font=f)
    return bbox[3] - bbox[1] + 6


def make_correct_photo_image() -> str:
    """Returns path to correct photo instruction image."""
    out = os.path.join(ASSETS_DIR, "instr_correct.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((W // 2, 28), "КАК СДЕЛАТЬ ПРАВИЛЬНОЕ ФОТО", font=_font(26),
              fill=GREEN, anchor="mm")

    # Divider line
    draw.line([(40, 60), (W - 40, 60)], fill=(50, 50, 70), width=1)

    # Face drawing on left
    face_cx, face_cy = 200, 290
    _draw_face_frontal(draw, face_cx, face_cy, GREEN)

    # Camera frame around face
    fw_r = 110
    draw.rectangle([face_cx - fw_r, face_cy - 140, face_cx + fw_r, face_cy + 130],
                   outline=(80, 80, 100), width=2)
    draw.text((face_cx, face_cy + 150), "📷 вид в камере", font=_font(16),
              fill=GREY, anchor="mm")

    # Green checkmark badge
    _badge(draw, img, face_cx - 40, face_cy - 185, "✓  ПРАВИЛЬНО", GREEN)

    # Center axis line
    draw.line([(face_cx, face_cy - 120), (face_cx, face_cy + 125)],
              fill=GREEN, width=1)

    # Divider
    _divider(draw, W // 2 - 10, 70, H - 30)

    # Rules on the right
    rx = W // 2 + 10
    ry = 80
    draw.text((rx + 190, ry), "ТРЕБОВАНИЯ", font=_font(20), fill=WHITE, anchor="mm")
    ry += 38

    rules = [
        "Смотрите строго в камеру",
        "Голова прямо, без наклонов",
        "Нейтральное выражение лица",
        "Лоб полностью открыт",
        "Равномерное освещение",
        "Расстояние: 40–60 см от камеры",
        "Фото чёткое, без размытия",
        "Подбородок виден, фон контрастный",
    ]
    for rule in rules:
        ry += _bullet(draw, rx + 10, ry, rule, WHITE)

    img.save(out, "PNG")
    return out


def make_wrong_photos_image() -> str:
    """Returns path to wrong photos instruction image."""
    out = os.path.join(ASSETS_DIR, "instr_wrong.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((W // 2, 28), "ЧТО ДЕЛАТЬ НЕЛЬЗЯ", font=_font(26),
              fill=RED, anchor="mm")
    draw.line([(40, 60), (W - 40, 60)], fill=(50, 50, 70), width=1)

    # Left panel: profile
    lx, ly = 200, 285
    _draw_face_profile(draw, lx, ly, RED)
    draw.rectangle([lx - 120, ly - 145, lx + 120, ly + 135],
                   outline=(80, 80, 100), width=2)
    _badge(draw, img, lx - 65, ly - 190, "✗  ПРОФИЛЬ", RED)
    draw.text((lx, ly + 160), "Лицо должно смотреть\nстрого в камеру",
              font=_font(15), fill=GREY, anchor="mm", align="center")

    # Divider
    _divider(draw, W // 2, 70, H - 30)

    # Right panel: tilted
    rx, ry = W - 200, 285
    _draw_face_tilted(draw, rx, ry, RED)
    draw.rectangle([rx - 120, ry - 145, rx + 120, ry + 135],
                   outline=(80, 80, 100), width=2)
    _badge(draw, img, rx - 70, ry - 190, "✗  НАКЛОН", RED)
    draw.text((rx, ry + 160), "Держите голову ровно,\nне наклоняйте к плечу",
              font=_font(15), fill=GREY, anchor="mm", align="center")

    img.save(out, "PNG")
    return out


def make_lighting_image() -> str:
    """Returns path to lighting instruction image."""
    out = os.path.join(ASSETS_DIR, "instr_lighting.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.text((W // 2, 28), "ОСВЕЩЕНИЕ И РАССТОЯНИЕ", font=_font(26),
              fill=YELLOW, anchor="mm")
    draw.line([(40, 60), (W - 40, 60)], fill=(50, 50, 70), width=1)

    # Good lighting panel (left)
    lx, ly = 200, 275

    # Sun icon (good)
    for angle in range(0, 360, 45):
        r   = math.radians(angle)
        x1  = lx - 120 + 50 + 28 * math.cos(r)
        y1  = ly - 130 + 40 + 28 * math.sin(r)
        x2  = lx - 120 + 50 + 44 * math.cos(r)
        y2  = ly - 130 + 40 + 44 * math.sin(r)
        draw.line([(x1, y1), (x2, y2)], fill=YELLOW, width=3)
    draw.ellipse([lx - 120 + 30, ly - 130 + 20, lx - 120 + 70, ly - 130 + 60],
                 fill=YELLOW)

    # Good face
    _draw_face_frontal(draw, lx, ly, GREEN)
    _badge(draw, img, lx - 55, ly - 195, "✓  ХОРОШО", GREEN)

    items_good = [
        "Свет спереди или сверху",
        "Равномерное освещение",
        "Без резких теней на лице",
        "40–60 см от камеры",
    ]
    iy = ly + 145
    for item in items_good:
        _bullet(draw, lx - 120, iy, item, GREEN, 16)
        iy += 24

    # Divider
    _divider(draw, W // 2, 70, H - 30)

    # Bad lighting panel (right)
    rx, ry = W - 185, 275

    # Single side light icon (bad)
    for angle in range(-30, 150, 40):
        r   = math.radians(angle)
        x1  = rx + 60 + 28 * math.cos(r)
        y1  = ry - 140 + 20 + 28 * math.sin(r)
        x2  = rx + 60 + 44 * math.cos(r)
        y2  = ry - 140 + 20 + 44 * math.sin(r)
        draw.line([(x1, y1), (x2, y2)], fill=RED, width=3)
    draw.ellipse([rx + 40, ry - 160 + 0, rx + 80, ry - 160 + 40], fill=RED)

    _draw_face_frontal(draw, rx, ry, RED)
    _badge(draw, img, rx - 60, ry - 195, "✗  ПЛОХО", RED)

    items_bad = [
        "Боковое освещение",
        "Тени закрывают черты лица",
        "Засветка с одной стороны",
        "Слишком близко к камере",
    ]
    iy = ry + 145
    for item in items_bad:
        _bullet(draw, rx - 120, iy, item, RED, 16)
        iy += 24

    img.save(out, "PNG")
    return out


def generate_all_instruction_images():
    """Generate all instruction images and return their paths."""
    paths = []
    for fn in (make_correct_photo_image, make_wrong_photos_image, make_lighting_image):
        try:
            p = fn()
            paths.append(p)
        except Exception as e:
            print(f"[instruction_images] Error generating {fn.__name__}: {e}")
    return paths


if __name__ == "__main__":
    paths = generate_all_instruction_images()
    print("Generated:", paths)
