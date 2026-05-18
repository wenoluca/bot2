"""
Generates 8 instruction images (one per rule) for the instruction PDF.
Dark theme, human silhouettes, ПРАВИЛЬНО / НЕПРАВИЛЬНО panels.
"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH  = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")

# Palette
BG     = (11, 11, 18)
PANEL  = (20, 20, 32)
CARD   = (26, 26, 40)
GREEN  = (72, 210, 130)
RED    = (230, 65, 65)
GOLD   = (218, 172, 40)
WHITE  = (232, 232, 245)
GREY   = (110, 110, 138)
LBLUE  = (90, 150, 225)
ORANGE = (230, 150, 40)

IW, IH = 900, 420   # image size per rule card

# ── Font helpers ──────────────────────────────────────────────────────────────
def _f(size):
    try:    return ImageFont.truetype(FONT_PATH, size)
    except: return ImageFont.load_default()

def _tw(draw, text, font):
    bb = draw.textbbox((0,0), text, font=font)
    return bb[2]-bb[0], bb[3]-bb[1]

def _tc(draw, cx, y, text, font, color):
    w, _ = _tw(draw, text, font)
    draw.text((cx - w//2, y), text, font=font, fill=color)

def _rr(draw, x1, y1, x2, y2, r, fill=None, outline=None, lw=2):
    draw.rounded_rectangle([x1,y1,x2,y2], radius=r, fill=fill, outline=outline, width=lw)


# ── Human silhouette primitives ───────────────────────────────────────────────

class Human:
    """Draws a schematic human (head + neck + shoulders) at (cx, cy)."""

    def __init__(self, draw, cx, cy, scale=1.0):
        self.d = draw
        self.cx = cx
        self.cy = cy
        self.s = scale
        self.hw = int(36 * scale)   # head half-width
        self.hh = int(46 * scale)   # head half-height
        self.ht = cy - int(128 * scale)  # head top y

    def head_center(self):
        return self.cx, self.ht + self.hh

    def draw_head(self, color=WHITE, bg=PANEL, tilt_deg=0, turn_deg=0):
        """Draw oval head, optionally tilted or turned."""
        d, cx, s = self.d, self.cx, self.s
        hcy = self.ht + self.hh   # head center y
        hw, hh = self.hw, self.hh

        if tilt_deg != 0:
            a = math.radians(tilt_deg)
            pts = []
            for i in range(0, 360, 6):
                r = math.radians(i)
                x = hw * math.cos(r)
                y = hh * math.sin(r)
                rx = x*math.cos(a) - y*math.sin(a) + cx
                ry = x*math.sin(a) + y*math.cos(a) + hcy
                pts.append((rx, ry))
            d.polygon(pts, fill=bg, outline=color)
        elif turn_deg != 0:
            # Squeeze head width to simulate horizontal rotation
            ratio = max(0.25, 1 - abs(turn_deg)/110)
            tw = max(8, int(hw * ratio))
            d.ellipse([cx-tw, self.ht, cx+tw, self.ht+hh*2], fill=bg, outline=color, width=2)
            # Draw profile nose
            side = 1 if turn_deg > 0 else -1
            nx = cx + side * tw
            ny = hcy + int(2*s)
            d.polygon([
                (nx, ny - int(12*s)),
                (nx + side*int(16*s), ny + int(6*s)),
                (nx + side*int(10*s), ny + int(18*s)),
                (nx, ny + int(16*s)),
            ], fill=bg, outline=color)
        else:
            d.ellipse([cx-hw, self.ht, cx+hw, self.ht+hh*2], fill=bg, outline=color, width=2)

        return hcy

    def draw_face_features(self, color=WHITE, tilt_deg=0, expression="neutral"):
        """Eyes, nose, mouth."""
        d, cx, s = self.d, self.cx, self.s
        hcy = self.ht + self.hh
        a = math.radians(tilt_deg)

        def rot(px, py):
            px -= cx; py -= hcy
            return cx + px*math.cos(a) - py*math.sin(a), \
                   hcy + px*math.sin(a) + py*math.cos(a)

        ey = hcy - int(12*s)
        for ex_off in (-int(15*s), int(15*s)):
            rx, ry = rot(cx+ex_off, ey)
            d.ellipse([rx-int(7*s), ry-int(5*s), rx+int(7*s), ry+int(5*s)], fill=color)
            d.ellipse([rx-int(4*s), ry-int(3*s), rx+int(4*s), ry+int(3*s)], fill=PANEL)

        # Nose
        rn1 = rot(cx, hcy+int(2*s))
        rn2 = rot(cx, hcy+int(14*s))
        d.line([rn1, rn2], fill=GREY, width=max(1,int(2*s)))
        rn3 = rot(cx-int(7*s), hcy+int(14*s))
        rn4 = rot(cx+int(7*s), hcy+int(14*s))
        d.line([rn3, rn4], fill=GREY, width=max(1,int(2*s)))

        # Mouth
        my = hcy + int(26*s)
        if expression == "neutral":
            rm1 = rot(cx-int(12*s), my)
            rm2 = rot(cx+int(12*s), my)
            d.line([rm1, rm2], fill=color, width=max(1,int(2*s)))
        elif expression == "smile":
            rm_bb = [cx-int(13*s), my-int(4*s), cx+int(13*s), my+int(10*s)]
            d.arc(rm_bb, 0, 180, fill=GREEN, width=max(2,int(3*s)))
        elif expression == "open":
            rx1, ry1 = rot(cx-int(10*s), my-int(2*s))
            rx2, ry2 = rot(cx+int(10*s), my+int(10*s))
            d.ellipse([min(rx1,rx2), min(ry1,ry2), max(rx1,rx2), max(ry1,ry2)], fill=RED)

    def draw_neck(self, color=WHITE):
        d, cx, s = self.d, self.cx, self.s
        nw = int(13*s)
        nt = self.ht + self.hh*2
        nb = nt + int(18*s)
        d.rectangle([cx-nw, nt, cx+nw, nb], fill=PANEL, outline=color, width=1)
        self.neck_bot = nb
        return nb

    def draw_shoulders(self, color=WHITE):
        d, cx, s = self.d, self.cx, self.s
        nb = getattr(self, 'neck_bot', self.ht + self.hh*2 + int(18*s))
        sw = int(65*s)
        sh = int(75*s)
        d.polygon([
            (cx-sw, nb+int(16*s)), (cx+sw, nb+int(16*s)),
            (cx+int(42*s), nb+sh), (cx-int(42*s), nb+sh),
        ], fill=PANEL, outline=color)

    def draw_full(self, color=WHITE, tilt_deg=0, turn_deg=0, expression="neutral"):
        self.draw_head(color, tilt_deg=tilt_deg, turn_deg=turn_deg)
        if turn_deg == 0:
            self.draw_face_features(color, tilt_deg=tilt_deg, expression=expression)
        self.draw_neck(color)
        self.draw_shoulders(color)

    def draw_hair(self, style="open"):
        """open = bun/back, bangs = covering forehead."""
        d, cx, s = self.d, self.cx, self.s
        if style == "bangs":
            # Heavy fringe
            for i in range(-self.hw, self.hw+1, 7):
                y0 = self.ht - int(4*s)
                y1 = self.ht + int(22*s) + abs(i)//4
                d.line([(cx+i, y0), (cx+i, y1)], fill=(110,72,28), width=3)
            d.arc([cx-self.hw+4, self.ht-8, cx+self.hw-4, self.ht+int(28*s)],
                  195, 345, fill=(90,58,20), width=7)
        else:
            d.arc([cx-self.hw, self.ht, cx+self.hw, self.ht+int(8*s)],
                  200, 340, fill=(110,72,28), width=4)
            bx, by = cx+self.hw-int(8*s), self.ht
            d.ellipse([bx-int(10*s), by, bx+int(10*s), by+int(22*s)],
                      fill=(110,72,28), outline=(90,58,20), width=2)

    def draw_guide_lines(self, color=GREEN):
        """Vertical + horizontal cross-hair alignment guides."""
        d, cx, s = self.d, self.cx, self.s
        top_y = self.ht - int(5*s)
        bot_y = self.ht + self.hh*2 + int(80*s)
        d.line([(cx, top_y), (cx, bot_y)], fill=(*color, 120), width=1)
        eye_y = self.ht + self.hh - int(12*s)
        d.line([(cx - int(75*s), eye_y), (cx + int(75*s), eye_y)], fill=(*color, 120), width=1)


def _badge(draw, cx, y1, correct: bool):
    color = GREEN if correct else RED
    sym   = "✓" if correct else "✗"
    label = "ПРАВИЛЬНО" if correct else "НЕПРАВИЛЬНО"
    text  = f" {sym}  {label} "
    f = _f(17)
    w, h = _tw(draw, text, f)
    x1, x2 = cx-w//2-10, cx+w//2+10
    y2 = y1 + h + 10
    draw.rounded_rectangle([x1, y1, x2, y2], radius=5, fill=color)
    draw.text((x1+10, y1+5), text, font=f, fill=BG)
    return y2 + 6

def _caption_block(draw, cx, y, lines, color=WHITE):
    f = _f(15)
    for line in lines:
        w, _ = _tw(draw, line, f)
        draw.text((cx-w//2, y), line, font=f, fill=color)
        y += 21
    return y

def _divider(draw):
    draw.line([(IW//2, 55), (IW//2, IH-10)], fill=(40,40,60), width=2)

def _base_image(title: str):
    img  = Image.new("RGB", (IW, IH), BG)
    draw = ImageDraw.Draw(img)
    # Top bar
    _rr(draw, 0, 0, IW, 50, 0, fill=(16, 16, 26))
    _tc(draw, IW//2, 10, title, _f(22), GOLD)
    _divider(draw)
    return img, draw


# ══════════════════════════════════════════════════════════════════════════════
# 8 rule images
# ══════════════════════════════════════════════════════════════════════════════

def _rule1_passport() -> str:
    """Rule 1: Photo like a passport (shoulders, front-facing)."""
    img, draw = _base_image("01  КАК НА ПАСПОРТ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    # LEFT — wrong: selfie angle / too close
    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy+10, scale=0.82)
    h.draw_full(color=(180,100,100))
    # Camera icon too close (large phone icon)
    draw.rectangle([lx-28, h.ht-55, lx+28, h.ht-20], outline=RED, width=2, fill=(30,18,18))
    _tc(draw, lx, h.ht-48, "📱", _f(22), RED)
    # Arrow showing too close
    draw.line([(lx, h.ht-20), (lx, h.ht-3)], fill=RED, width=3)
    _caption_block(draw, lx, IH-68, ["Слишком близко — часть лица", "обрезана, пропорции искажены"], RED)

    # RIGHT — correct: full passport style
    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE)
    # Camera icon at correct distance
    draw.rectangle([rx-18, h2.ht-70, rx+18, h2.ht-40], outline=GREEN, width=2, fill=(16,26,18))
    _tc(draw, rx, h2.ht-64, "📷", _f(18), GREEN)
    # Frame around face+shoulders
    _rr(draw, rx-85, h2.ht-10, rx+85, h2.ht+h2.hh*2+90, 4,
        outline=(90,200,130), fill=None, lw=2)
    _caption_block(draw, rx, IH-68, ["Анфас, плечи в кадре,", "лицо строго по центру"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule1_passport.png"), "PNG")
    return p


def _rule2_frontal() -> str:
    """Rule 2: Look straight into the camera (not profile)."""
    img, draw = _base_image("02  СМОТРИТЕ ПРЯМО В КАМЕРУ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_full(color=(180,80,80), turn_deg=55)
    # Arrow showing turn
    ax = lx + int(h.hw * 0.6)
    ay = h.ht + h.hh
    for i in range(3):
        draw.arc([ax+i*4, ay-22, ax+i*4+32, ay+22], -70, 70, fill=RED, width=2)
    _caption_block(draw, lx, IH-68, ["Поворот головы — анализ", "не видит обе стороны лица"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE, expression="neutral")
    # Camera bullseye
    for r in (30, 22, 14):
        draw.ellipse([rx-r, h2.ht-55-r, rx+r, h2.ht-55+r], outline=GREEN, width=1)
    draw.ellipse([rx-5, h2.ht-60, rx+5, h2.ht-50], fill=GREEN)
    _caption_block(draw, rx, IH-68, ["Глаза смотрят прямо в камеру,", "лицо симметрично по центру"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule2_frontal.png"), "PNG")
    return p


def _rule3_no_rotation() -> str:
    """Rule 3: Head straight — no horizontal turns."""
    img, draw = _base_image("03  ГОЛОВА РОВНО — БЕЗ ПОВОРОТОВ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_full(color=(180,80,80), turn_deg=35)
    # Curved rotation arrow
    draw.arc([lx-50, h.ht+h.hh-38, lx+50, h.ht+h.hh+38], 200, 320, fill=RED, width=3)
    draw.line([(lx-34, h.ht+h.hh+26), (lx-34, h.ht+h.hh+40)], fill=RED, width=3)
    draw.line([(lx-34, h.ht+h.hh+26), (lx-20, h.ht+h.hh+26)], fill=RED, width=3)
    _caption_block(draw, lx, IH-68, ["Горизонтальный поворот головы", "скрывает черты лица"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE)
    # Vertical guide arrow
    draw.line([(rx, h2.ht-12), (rx, h2.ht+h2.hh*2+85)], fill=GREEN, width=2)
    _caption_block(draw, rx, IH-68, ["Носовая ось строго вертикальна,", "оба уха одинаково видны"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule3_rotation.png"), "PNG")
    return p


def _rule4_no_tilt() -> str:
    """Rule 4: No head tilt toward shoulder."""
    img, draw = _base_image("04  БЕЗ НАКЛОНА К ПЛЕЧУ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_neck(RED)
    h.draw_shoulders(RED)
    h.draw_head(RED, tilt_deg=22)
    h.draw_face_features(RED, tilt_deg=22, expression="neutral")
    # Arc arrow showing tilt
    draw.arc([lx+30, h.ht+h.hh-30, lx+90, h.ht+h.hh+30], -60, 30, fill=RED, width=3)
    draw.line([(lx+61, h.ht+h.hh-28), (lx+78, h.ht+h.hh-22)], fill=RED, width=3)
    _caption_block(draw, lx, IH-68, ["Наклон к плечу перекашивает", "все горизонтальные метрики"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE)
    # Horizontal eye level line highlight
    ey = h2.ht + h2.hh - int(12*0.82)
    draw.line([(rx-72, ey), (rx+72, ey)], fill=GREEN, width=2)
    _tc(draw, rx+85, ey-8, "—", _f(18), GREEN)
    _caption_block(draw, rx, IH-68, ["Голова ровная, линия глаз", "строго горизонтальна"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule4_tilt.png"), "PNG")
    return p


def _rule5_hair() -> str:
    """Rule 5: Open forehead — hair back."""
    img, draw = _base_image("05  ЛОБ ДОЛЖЕН БЫТЬ ОТКРЫТ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_full(color=(180,80,80))
    h.draw_hair(style="bangs")
    # Red X over forehead
    ft = h.ht + int(5*0.82)
    fb = h.ht + int(28*0.82)
    draw.line([(lx-22, ft), (lx+22, fb)], fill=RED, width=3)
    draw.line([(lx+22, ft), (lx-22, fb)], fill=RED, width=3)
    _caption_block(draw, lx, IH-68, ["Чёлка закрывает лоб —", "алгоритм теряет ключевые точки"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE)
    h2.draw_hair(style="open")
    # Green checkmark over forehead
    ft2 = h2.ht + int(4*0.82)
    draw.line([(rx-15, ft2+12), (rx-4, ft2+22), (rx+18, ft2)], fill=GREEN, width=3)
    _caption_block(draw, rx, IH-68, ["Лоб полностью открыт,", "волосы убраны назад или заколоты"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule5_hair.png"), "PNG")
    return p


def _rule6_expression() -> str:
    """Rule 6: Neutral expression — no smiling."""
    img, draw = _base_image("06  НЕЙТРАЛЬНОЕ ВЫРАЖЕНИЕ ЛИЦА")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_head((180,80,80))
    h.draw_face_features((180,80,80), expression="smile")
    h.draw_neck((180,80,80))
    h.draw_shoulders((180,80,80))
    _caption_block(draw, lx, IH-68, ["Улыбка смещает точки губ", "и мышцы скул — метрики врут"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE, expression="neutral")
    _caption_block(draw, rx, IH-68, ["Расслабленное лицо, рот закрыт,", "мышцы не напряжены"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule6_expression.png"), "PNG")
    return p


def _rule7_lighting() -> str:
    """Rule 7: Even front lighting — no harsh shadows."""
    img, draw = _base_image("07  РОВНОЕ ОСВЕЩЕНИЕ БЕЗ ТЕНЕЙ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    _badge(draw, lx, 56, False)
    h = Human(draw, lx, cy, scale=0.82)
    h.draw_full(color=(160,160,185))
    # Side lamp
    lamp_x, lamp_y = lx+105, 85
    draw.ellipse([lamp_x-12, lamp_y-12, lamp_x+12, lamp_y+12], fill=RED)
    for a_deg in range(-50, 110, 30):
        a = math.radians(a_deg)
        x1 = lamp_x + int(16*math.cos(a))
        y1 = lamp_y + int(16*math.sin(a))
        x2 = lamp_x + int(28*math.cos(a))
        y2 = lamp_y + int(28*math.sin(a))
        draw.line([(x1,y1),(x2,y2)], fill=RED, width=2)
    # Shadow half-overlay
    sx = lx - h.hw + 4
    shadow_pts = [(sx, h.ht+2), (lx-2, h.ht+2),
                  (lx-2, h.ht+h.hh*2-2), (sx, h.ht+h.hh*2-2)]
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    ov_d = ImageDraw.Draw(overlay)
    ov_d.polygon(shadow_pts, fill=(10,10,18,160))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img.paste(img_rgba.convert("RGB"))
    draw = ImageDraw.Draw(img)
    _caption_block(draw, lx, IH-68, ["Боковой свет — половина лица", "в тени, метрики недостоверны"], RED)

    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_full(color=WHITE)
    # Sun above face
    sx2, sy2 = rx, h2.ht - 42
    draw.ellipse([sx2-14, sy2-14, sx2+14, sy2+14], fill=GOLD)
    for a_deg in range(0, 360, 40):
        a = math.radians(a_deg)
        draw.line([(sx2+int(18*math.cos(a)), sy2+int(18*math.sin(a))),
                   (sx2+int(30*math.cos(a)), sy2+int(30*math.sin(a)))], fill=GOLD, width=2)
    # Light cone
    draw.polygon([(rx-18, sy2+14), (rx+18, sy2+14),
                  (rx+50, h2.ht), (rx-50, h2.ht)], fill=(30,28,10))
    _caption_block(draw, rx, IH-68, ["Равномерный свет спереди,", "лицо без теней и бликов"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule7_lighting.png"), "PNG")
    return p


def _rule8_sharpness() -> str:
    """Rule 8: Sharp photo — no blur."""
    img, draw = _base_image("08  ЧЁТКОЕ ФОТО БЕЗ РАЗМЫТИЯ")
    cy = IH//2 + 24
    lx, rx = IW//4, IW*3//4

    # LEFT — blurry: draw human then apply gaussian blur to a subsection
    _badge(draw, lx, 56, False)

    # Render left side into a temp surface, blur it
    tmp = Image.new("RGB", (IW//2, IH), BG)
    td  = ImageDraw.Draw(tmp)
    ht = Human(td, IW//4, cy, scale=0.82)
    ht.draw_full(color=(180,100,100))

    tmp_blurred = tmp.filter(ImageFilter.GaussianBlur(radius=4))
    img.paste(tmp_blurred.crop((0,0,IW//2,IH)), (0,0))

    draw = ImageDraw.Draw(img)
    _divider(draw)
    # Re-draw badge (was under blurred layer)
    _badge(draw, lx, 56, False)
    # Motion blur lines
    for yy in (cy - 60, cy - 20, cy + 20):
        draw.line([(lx-60, yy), (lx+60, yy+4)], fill=(*RED, 120), width=2)
    _caption_block(draw, lx, IH-68, ["Размытое фото — алгоритм", "не находит точки лица"], RED)

    # RIGHT — sharp
    _badge(draw, rx, 56, True)
    h2 = Human(draw, rx, cy, scale=0.82)
    h2.draw_guide_lines(GREEN)
    h2.draw_full(color=WHITE)
    # Sharp detail marks
    for off in (-28, 0, 28):
        draw.rectangle([rx+off-3, h2.ht+h2.hh+off//2-3,
                        rx+off+3, h2.ht+h2.hh+off//2+3], fill=LBLUE)
    _caption_block(draw, rx, IH-68, ["Резкий снимок, 98 точек лица", "определяются без ошибок"], GREEN)

    img.save(p := os.path.join(ASSETS_DIR, "rule8_sharpness.png"), "PNG")
    return p


RULE_GENERATORS = [
    _rule1_passport,
    _rule2_frontal,
    _rule3_no_rotation,
    _rule4_no_tilt,
    _rule5_hair,
    _rule6_expression,
    _rule7_lighting,
    _rule8_sharpness,
]

RULE_TITLES = [
    "КАК НА ПАСПОРТ",
    "СМОТРИТЕ ПРЯМО В КАМЕРУ",
    "ГОЛОВА РОВНО — БЕЗ ПОВОРОТОВ",
    "БЕЗ НАКЛОНА К ПЛЕЧУ",
    "ЛОБ ДОЛЖЕН БЫТЬ ОТКРЫТ",
    "НЕЙТРАЛЬНОЕ ВЫРАЖЕНИЕ",
    "РОВНОЕ ОСВЕЩЕНИЕ БЕЗ ТЕНЕЙ",
    "ЧЁТКОЕ ФОТО БЕЗ РАЗМЫТИЯ",
]

RULE_DESCS = [
    ("Плечи в кадре, лицо по центру,",
     "как фото на паспорт или документ."),
    ("Смотрите в объектив, не в сторону.",
     "Оба глаза должны быть видны одинаково."),
    ("Нос смотрит строго вертикально.",
     "Оба уха симметрично видны в кадре."),
    ("Голова не наклонена к плечу.",
     "Линия глаз строго горизонтальна."),
    ("Уберите волосы с лица и лба.",
     "Линия роста волос должна быть видна."),
    ("Расслабленное лицо, рот закрыт.",
     "Не улыбайтесь, не хмурьтесь."),
    ("Свет падает спереди, равномерно.",
     "Избегайте теней и засветки."),
    ("Снимайте на хорошую камеру.",
     "Фото должно быть резким и чётким."),
]


def generate_all_rule_images() -> list:
    """Generate all 8 rule images, return list of paths."""
    paths = []
    for fn in RULE_GENERATORS:
        try:
            p = fn()
            paths.append(p)
        except Exception as e:
            print(f"[instruction_images] Error in {fn.__name__}: {e}")
    return paths


# Legacy names for backward compat
def generate_all_instruction_images():
    return generate_all_rule_images()


if __name__ == "__main__":
    paths = generate_all_rule_images()
    print("Generated:", len(paths), "images")
    for p in paths:
        print(" ", p)
