"""
Generates instruction images showing correct/incorrect photo poses.
Uses realistic human silhouettes drawn with Pillow.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH  = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")

BG      = (14, 14, 22)
PANEL   = (22, 22, 34)
GREEN   = (80, 210, 140)
RED     = (235, 70, 70)
GOLD    = (220, 180, 50)
WHITE   = (235, 235, 248)
GREY    = (120, 120, 145)
LBLUE   = (100, 160, 230)

W, H = 960, 560


def _font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _text_center(draw, y, text, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)


def _rounded_rect(draw, x1, y1, x2, y2, r, fill=None, outline=None, width=2):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)


# ─── Human silhouette drawing functions ──────────────────────────────────────

def _draw_human_frontal(draw, cx, cy, scale=1.0, color=WHITE, alpha_bg=None):
    """Draw a front-facing human silhouette."""
    s = scale

    # Head (oval)
    hw, hh = int(38 * s), int(48 * s)
    head_top = cy - int(130 * s)
    draw.ellipse([cx - hw, head_top, cx + hw, head_top + hh * 2],
                 outline=color, width=max(2, int(3 * s)), fill=PANEL)

    # Neck
    nw = int(14 * s)
    neck_top = head_top + hh * 2
    neck_bot = neck_top + int(18 * s)
    draw.rectangle([cx - nw, neck_top, cx + nw, neck_bot], fill=PANEL, outline=color,
                   width=max(1, int(2 * s)))

    # Shoulders + torso
    sw = int(70 * s)
    sh = int(90 * s)
    tor_top = neck_bot
    tor_bot = tor_top + sh
    # Trapezoid shoulders
    draw.polygon([
        (cx - sw, tor_top + int(20 * s)),
        (cx + sw, tor_top + int(20 * s)),
        (cx + int(45 * s), tor_bot),
        (cx - int(45 * s), tor_bot),
    ], outline=color, fill=PANEL)

    # Eyes
    ey = head_top + int(22 * s)
    ew = int(8 * s)
    for ex in (cx - int(16 * s), cx + int(16 * s)):
        draw.ellipse([ex - ew, ey - int(5 * s), ex + ew, ey + int(5 * s)],
                     fill=color)
        draw.ellipse([ex - int(4 * s), ey - int(3 * s), ex + int(4 * s), ey + int(3 * s)],
                     fill=PANEL)

    # Nose
    ny = ey + int(16 * s)
    draw.line([(cx, ny), (cx, ny + int(12 * s))], fill=GREY, width=max(1, int(2 * s)))
    draw.line([(cx - int(7 * s), ny + int(12 * s)), (cx + int(7 * s), ny + int(12 * s))],
              fill=GREY, width=max(1, int(2 * s)))

    # Mouth
    my = ny + int(20 * s)
    draw.arc([cx - int(14 * s), my - int(5 * s), cx + int(14 * s), my + int(10 * s)],
             0, 180, fill=color, width=max(1, int(2 * s)))

    return head_top, tor_bot


def _draw_human_profile(draw, cx, cy, scale=1.0, color=RED, facing_left=True):
    """Draw a side-profile human silhouette."""
    s = scale
    d = -1 if facing_left else 1

    hw, hh = int(30 * s), int(46 * s)
    head_top = cy - int(130 * s)
    head_cx = cx + d * int(10 * s)

    # Head oval (shifted to show profile)
    draw.ellipse([head_cx - hw, head_top, head_cx + hw, head_top + hh * 2],
                 outline=color, width=3, fill=PANEL)

    # Nose bump (profile)
    nose_y = head_top + int(30 * s)
    nose_x = head_cx + d * hw
    draw.polygon([
        (nose_x, nose_y),
        (nose_x + d * int(18 * s), nose_y + int(10 * s)),
        (nose_x + d * int(12 * s), nose_y + int(22 * s)),
        (nose_x, nose_y + int(20 * s)),
    ], fill=PANEL, outline=color)

    # One eye
    ey = head_top + int(22 * s)
    ex = head_cx + d * int(8 * s)
    draw.ellipse([ex - int(8 * s), ey - int(5 * s), ex + int(8 * s), ey + int(5 * s)],
                 fill=color)

    # Lips
    ly = head_top + int(60 * s)
    lx = head_cx + d * (hw - int(5 * s))
    draw.arc([lx - int(10 * s), ly - int(6 * s), lx + int(10 * s), ly + int(6 * s)],
             180 if facing_left else 0, 360 if facing_left else 180, fill=color, width=2)

    # Neck + shoulders (still frontal-ish)
    nw = int(14 * s)
    neck_top = head_top + hh * 2
    neck_bot = neck_top + int(18 * s)
    draw.rectangle([cx - nw, neck_top, cx + nw, neck_bot], fill=PANEL, outline=color, width=2)
    sw = int(65 * s)
    sh = int(80 * s)
    draw.polygon([
        (cx - sw, neck_bot + int(20 * s)),
        (cx + sw, neck_bot + int(20 * s)),
        (cx + int(42 * s), neck_bot + sh),
        (cx - int(42 * s), neck_bot + sh),
    ], outline=color, fill=PANEL)

    # Big red arrow showing it's turned
    ax = cx + d * int(60 * s)
    ay = head_top + int(44 * s)
    draw.line([(ax, ay), (ax + d * int(35 * s), ay)], fill=RED, width=4)
    # Arrow head
    for offset in range(1, 10):
        draw.line([(ax + d * int(35 * s), ay),
                   (ax + d * int(35 * s) - d * offset, ay - offset)], fill=RED, width=3)
        draw.line([(ax + d * int(35 * s), ay),
                   (ax + d * int(35 * s) - d * offset, ay + offset)], fill=RED, width=3)


def _draw_human_tilted(draw, cx, cy, scale=1.0, tilt_deg=22):
    """Draw a human with tilted head (toward shoulder)."""
    s = scale
    angle = math.radians(tilt_deg)

    def rot(px, py, origin_x, origin_y):
        px -= origin_x; py -= origin_y
        rx = px * math.cos(angle) - py * math.sin(angle)
        ry = px * math.sin(angle) + py * math.cos(angle)
        return rx + origin_x, ry + origin_y

    hw, hh = int(38 * s), int(48 * s)
    head_top = cy - int(130 * s)
    head_cx = cx
    head_cy = head_top + hh
    pivot = (head_cx, head_cy)

    # Rotated head oval (approximate as polygon)
    pts = []
    for i in range(0, 360, 8):
        r = math.radians(i)
        x = head_cx + hw * math.cos(r)
        y = head_cy + hh * math.sin(r)
        rx, ry = rot(x, y, *pivot)
        pts.append((rx, ry))
    draw.polygon(pts, outline=RED, fill=PANEL)

    # Eyes (rotated)
    ey = head_cy - int(10 * s)
    for ex_off in (-int(16 * s), int(16 * s)):
        rx, ry = rot(head_cx + ex_off, ey, *pivot)
        draw.ellipse([rx - int(7 * s), ry - int(4 * s), rx + int(7 * s), ry + int(4 * s)],
                     fill=RED)

    # Nose line (rotated)
    ny = head_cy + int(8 * s)
    rn1 = rot(head_cx, ny, *pivot)
    rn2 = rot(head_cx, ny + int(14 * s), *pivot)
    draw.line([rn1, rn2], fill=GREY, width=2)

    # Neck + shoulders (not rotated)
    nw = int(14 * s)
    neck_top = head_top + hh * 2 + int(5 * s)
    neck_bot = neck_top + int(18 * s)
    draw.rectangle([cx - nw, neck_top, cx + nw, neck_bot], fill=PANEL, outline=RED, width=2)
    sw = int(65 * s)
    sh = int(80 * s)
    draw.polygon([
        (cx - sw, neck_bot + int(20 * s)),
        (cx + sw, neck_bot + int(20 * s)),
        (cx + int(42 * s), neck_bot + sh),
        (cx - int(42 * s), neck_bot + sh),
    ], outline=RED, fill=PANEL)

    # Curved arrow showing tilt
    ax, ay = cx + int(65 * s), head_cy - int(20 * s)
    draw.arc([ax - int(25 * s), ay - int(25 * s), ax + int(25 * s), ay + int(25 * s)],
             -30, 60, fill=RED, width=3)


def _draw_human_hair(draw, cx, cy, scale=1.0, cover=False, color=WHITE):
    """Draw hair - either covering forehead (wrong) or pulled back (right)."""
    s = scale
    hw, hh = int(38 * s), int(48 * s)
    head_top = cy - int(130 * s)
    head_cy = head_top + hh

    if cover:
        # Hair covering forehead
        for i in range(0, 12):
            hx = cx - hw + i * int(7 * s)
            hy_start = head_top - int(5 * s)
            hy_end = head_top + int(25 * s) + (i % 3) * int(5 * s)
            draw.line([(hx, hy_start), (hx, hy_end)], fill=(120, 80, 40), width=3)
        # Fringe covering eyes
        draw.arc([cx - hw + int(5 * s), head_top - int(8 * s),
                  cx + hw - int(5 * s), head_top + int(35 * s)],
                 200, 340, fill=(100, 65, 30), width=8)
    else:
        # Hair pulled back (just a bun hint)
        draw.arc([cx - hw, head_top, cx + hw, head_top + int(10 * s)],
                 200, 340, fill=(120, 80, 40), width=5)
        draw.ellipse([cx + hw - int(12 * s), head_top,
                      cx + hw + int(12 * s), head_top + int(24 * s)],
                     fill=(120, 80, 40), outline=(100, 65, 30), width=2)


def _draw_camera_frame(draw, cx, cy, scale=1.0, color=LBLUE):
    """Draw camera viewfinder frame around person."""
    s = scale
    fw = int(110 * s)
    fh = int(160 * s)
    fy = cy - int(145 * s)
    draw.rectangle([cx - fw, fy, cx + fw, fy + fh], outline=color, width=2)
    # Corner markers
    cl = 18
    for px, py in [(cx - fw, fy), (cx + fw, fy), (cx - fw, fy + fh), (cx + fw, fy + fh)]:
        dx = 1 if px < cx else -1
        dy = 1 if py < cy else -1
        draw.line([(px, py), (px + dx * cl, py)], fill=color, width=3)
        draw.line([(px, py), (px, py + dy * cl)], fill=color, width=3)


def _draw_axis_lines(draw, cx, cy, scale=1.0, color=GREEN, correct=True):
    """Draw vertical/horizontal reference lines."""
    s = scale
    if correct:
        # Vertical center line (straight)
        draw.line([(cx, cy - int(145 * s)), (cx, cy + int(10 * s))],
                  fill=color, width=1)
        # Horizontal eye line (straight)
        draw.line([(cx - int(90 * s), cy - int(108 * s)), (cx + int(90 * s), cy - int(108 * s))],
                  fill=color, width=1)
    else:
        # Diagonal lines showing misalignment
        draw.line([(cx - int(40 * s), cy - int(145 * s)), (cx + int(40 * s), cy - int(100 * s))],
                  fill=RED, width=2)


def _panel_header(draw, x1, y1, x2, label, is_correct):
    """Draw the ПРАВИЛЬНО / НЕПРАВИЛЬНО badge."""
    color = GREEN if is_correct else RED
    symbol = "✓" if is_correct else "✗"
    text = f"  {symbol}  {'ПРАВИЛЬНО' if is_correct else 'НЕПРАВИЛЬНО'}  "
    f = _font(18)
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = (x1 + x2) // 2
    bx1, bx2 = cx - tw // 2 - 12, cx + tw // 2 + 12
    by1, by2 = y1 + 10, y1 + 10 + th + 12
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=6, fill=color)
    draw.text((bx1 + 12, by1 + 6), text, font=f, fill=BG)
    return by2 + 8


def _caption(draw, cx, y, text, color=WHITE):
    """Draw caption text centered at cx."""
    f = _font(16)
    lines = text.split("\n")
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=f)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, y), line, font=f, fill=color)
        y += 22
    return y


# ─── Image generators ─────────────────────────────────────────────────────────

def make_image_1_frontal_vs_profile() -> str:
    """Image 1: Correct frontal vs wrong profile view."""
    out = os.path.join(ASSETS_DIR, "instr_correct.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    _rounded_rect(draw, 0, 0, W, 52, 0, fill=(20, 20, 32))
    _text_center(draw, 10, "ПРАВИЛЬНАЯ ПОСТАНОВКА", _font(26), GOLD)
    _text_center(draw, 38, "Лицо строго в камеру — основное требование", _font(16), GREY)

    # Divider
    draw.line([(W // 2, 60), (W // 2, H - 20)], fill=(45, 45, 65), width=2)

    # LEFT PANEL — CORRECT (frontal)
    lx = W // 4
    ly = H // 2 + 20
    _panel_header(draw, 10, 58, W // 2 - 10, "", True)
    _draw_axis_lines(draw, lx, ly, scale=1.0, color=GREEN, correct=True)
    _draw_camera_frame(draw, lx, ly, scale=1.0, color=LBLUE)
    _draw_human_frontal(draw, lx, ly, scale=1.0, color=WHITE)

    _caption(draw, lx, H - 95,
             "Лицо смотрит прямо в камеру\nАнфас — все черты видны чётко", GREEN)

    # RIGHT PANEL — WRONG (profile)
    rx = W * 3 // 4
    ry = H // 2 + 20
    _panel_header(draw, W // 2 + 10, 58, W - 10, "", False)
    _draw_camera_frame(draw, rx, ry, scale=1.0, color=(80, 80, 100))
    _draw_human_profile(draw, rx, ry, scale=1.0, color=RED, facing_left=True)

    _caption(draw, rx, H - 95,
             "Профиль или поворот — алгоритм\nне видит обе стороны лица", RED)

    img.save(out, "PNG")
    return out


def make_image_2_tilt_and_hair() -> str:
    """Image 2: Wrong tilted head vs wrong hair covering face vs correct."""
    out = os.path.join(ASSETS_DIR, "instr_wrong.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    _rounded_rect(draw, 0, 0, W, 52, 0, fill=(20, 20, 32))
    _text_center(draw, 10, "ЧАСТЫЕ ОШИБКИ", _font(26), RED)
    _text_center(draw, 38, "Эти позы дают неверный результат анализа", _font(16), GREY)

    # Three panels
    third = W // 3
    for i, x in enumerate([third // 2, W // 2, third * 2 + third // 2]):
        draw.line([(third * i, 56), (third * i, H - 20)], fill=(38, 38, 58), width=2)

    cy = H // 2 + 20

    # Panel 1: Tilted head
    x1 = third // 2
    _panel_header(draw, 5, 58, third - 5, "", False)
    _draw_human_tilted(draw, x1, cy, scale=0.9, tilt_deg=26)
    _caption(draw, x1, H - 90,
             "Наклон головы к плечу\nискажает все горизонтали", RED)

    # Panel 2: Hair covering
    x2 = W // 2
    _panel_header(draw, third + 5, 58, third * 2 - 5, "", False)
    _draw_human_frontal(draw, x2, cy, scale=0.9, color=(180, 180, 200))
    _draw_human_hair(draw, x2, cy, scale=0.9, cover=True)
    _caption(draw, x2, H - 90,
             "Волосы закрывают лоб и\nмешают определить точки", RED)

    # Panel 3: Correct — clean, open face
    x3 = third * 2 + third // 2
    _panel_header(draw, third * 2 + 5, 58, W - 5, "", True)
    _draw_axis_lines(draw, x3, cy, scale=0.9, color=GREEN, correct=True)
    _draw_human_frontal(draw, x3, cy, scale=0.9, color=WHITE)
    _draw_human_hair(draw, x3, cy, scale=0.9, cover=False)
    _caption(draw, x3, H - 90,
             "Голова ровно, лоб открыт\nнейтральное выражение", GREEN)

    img.save(out, "PNG")
    return out


def make_image_3_lighting() -> str:
    """Image 3: Good vs bad lighting."""
    out = os.path.join(ASSETS_DIR, "instr_lighting.png")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    _rounded_rect(draw, 0, 0, W, 52, 0, fill=(20, 20, 32))
    _text_center(draw, 10, "ОСВЕЩЕНИЕ И КАЧЕСТВО ФОТО", _font(26), GOLD)
    _text_center(draw, 38, "Свет спереди — ключ к точному анализу", _font(16), GREY)

    draw.line([(W // 2, 60), (W // 2, H - 20)], fill=(45, 45, 65), width=2)

    cy = H // 2 + 20

    # LEFT — CORRECT lighting
    lx = W // 4
    _panel_header(draw, 10, 58, W // 2 - 10, "", True)

    # Sun rays from above/front (left panel)
    sun_x, sun_y = lx, 90
    draw.ellipse([sun_x - 18, sun_y - 18, sun_x + 18, sun_y + 18], fill=GOLD)
    for angle_deg in range(0, 360, 40):
        a = math.radians(angle_deg)
        x1 = sun_x + int(22 * math.cos(a))
        y1 = sun_y + int(22 * math.sin(a))
        x2 = sun_x + int(36 * math.cos(a))
        y2 = sun_y + int(36 * math.sin(a))
        draw.line([(x1, y1), (x2, y2)], fill=GOLD, width=3)

    # Light cone going toward face
    draw.polygon([
        (sun_x - 20, sun_y + 18),
        (sun_x + 20, sun_y + 18),
        (lx + 45, cy - 130),
        (lx - 45, cy - 130),
    ], fill=(40, 40, 20))

    _draw_human_frontal(draw, lx, cy, scale=1.0, color=WHITE)
    # Bright face highlight
    hw, hh = 38, 48
    head_top = cy - 130
    draw.ellipse([lx - hw + 4, head_top + 4, lx + hw - 4, head_top + hh * 2 - 4],
                 fill=(35, 35, 28))

    _caption(draw, lx, H - 100,
             "Равномерный свет спереди\nЧёткое фото без теней", GREEN)

    # RIGHT — BAD lighting (side shadow)
    rx = W * 3 // 4
    _panel_header(draw, W // 2 + 10, 58, W - 10, "", False)

    # Side lamp (wrong)
    lamp_x, lamp_y = rx + 100, 110
    draw.ellipse([lamp_x - 14, lamp_y - 14, lamp_x + 14, lamp_y + 14], fill=RED)
    for angle_deg in range(-60, 120, 35):
        a = math.radians(angle_deg)
        x1 = lamp_x + int(18 * math.cos(a))
        y1 = lamp_y + int(18 * math.sin(a))
        x2 = lamp_x + int(30 * math.cos(a))
        y2 = lamp_y + int(30 * math.sin(a))
        draw.line([(x1, y1), (x2, y2)], fill=RED, width=2)

    # Shadow overlay on half of face
    _draw_human_frontal(draw, rx, cy, scale=1.0, color=(160, 160, 180))

    # Dark shadow half
    head_top_r = cy - 130
    hw_r, hh_r = 38, 48
    shadow_pts = [
        (rx, head_top_r - 2),
        (rx - hw_r, head_top_r + 20),
        (rx - hw_r, head_top_r + hh_r * 2 - 10),
        (rx, head_top_r + hh_r * 2),
    ]
    draw.polygon(shadow_pts, fill=(14, 14, 22))

    # X mark
    draw.line([(rx - hw_r - 5, head_top_r), (rx + 5, head_top_r + hh_r * 2 + 5)],
              fill=RED, width=3)

    _caption(draw, rx, H - 100,
             "Боковой свет даёт тени\nПолутёмное лицо — ошибки в метриках", RED)

    img.save(out, "PNG")
    return out


def generate_all_instruction_images():
    """Generate all instruction images and return their paths."""
    paths = []
    for fn in (make_image_1_frontal_vs_profile,
               make_image_2_tilt_and_hair,
               make_image_3_lighting):
        try:
            p = fn()
            paths.append(p)
        except Exception as e:
            print(f"[instruction_images] Error in {fn.__name__}: {e}")
    return paths


if __name__ == "__main__":
    paths = generate_all_instruction_images()
    print("Generated:", paths)
