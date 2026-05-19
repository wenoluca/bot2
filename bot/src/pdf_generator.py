"""
PDF-генератор Facedex — тёмная тема, мужской лукс-мэксинг.
Краткий разбор: 2 страницы.
Полный разбор:  25 страниц.
"""
import io
import os
import math

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from face_analyzer import FaceMetrics

# ── Шрифты ───────────────────────────────────────────────────────────────────
_FP = os.path.join(os.path.dirname(__file__), "..", "assets", "DejaVuSans.ttf")
try:
    pdfmetrics.registerFont(TTFont("DV",  _FP))
    pdfmetrics.registerFont(TTFont("DVB", _FP))
except Exception:
    pass
R, B = "DV", "DVB"

# ── Размеры ───────────────────────────────────────────────────────────────────
W, H = A4           # 595.28 × 841.89 pt
ML = 20 * mm        # left margin
MR = 20 * mm        # right margin
MT = 16 * mm        # top margin
MB = 14 * mm        # bottom margin
BW = W - ML - MR   # body width ≈ 481 pt

# ── Цвета (тёмная тема) ───────────────────────────────────────────────────────
BG        = colors.HexColor("#0C0C0C")    # фон страниц
SURFACE   = colors.HexColor("#181818")   # поверхность карточек
CARD      = colors.HexColor("#222222")   # карточки светлее
PANEL     = colors.HexColor("#2A2A2A")   # панели/секции
WHITE_TXT = colors.HexColor("#EEEEEE")   # основной текст
DIM       = colors.HexColor("#777777")   # приглушённый текст
LINE      = colors.HexColor("#333333")   # разделители
C_HIGH    = colors.HexColor("#00E676")   # зелёный — высокий балл
C_MID     = colors.HexColor("#FF9100")   # оранжевый — средний
C_LOW     = colors.HexColor("#FF1744")   # красный — низкий
GOLD      = colors.HexColor("#FFD700")   # золотой акцент
INFL_BG   = colors.HexColor("#0D1B3E")   # блок влияния
INFL_BD   = colors.HexColor("#4A6CF7")   # граница блока влияния
SCORE_BG  = SURFACE

BOT    = "Facedex Bot"
HANDLE = "@facedex_bot"

# ── Вспомогательные ──────────────────────────────────────────────────────────
def _c(y_top): return H - y_top

def _sc(s):
    if s >= 7.5: return C_HIGH
    if s >= 5.5: return C_MID
    return C_LOW

def _lv(s):
    if s >= 9.0: return "Исключительно"
    if s >= 7.5: return "Выше среднего"
    if s >= 5.5: return "Среднее"
    if s >= 4.0: return "Ниже среднего"
    return "Низко"


def _lv_desc(s):
    """Расшифровка уровня — что именно означает этот балл для данной метрики."""
    if s >= 9.0: return "Топ 3% — редкое сочетание пропорций"
    if s >= 7.5: return "Заметно выигрышная черта, усиливает общее впечатление"
    if s >= 5.5: return "В пределах нормы, не выделяется ни в плюс ни в минус"
    if s >= 4.0: return "Слабое место — стоит проработать в первую очередь"
    return "Приоритетная зона роста, заметно снижает гармонию"

def _tier_label(t):
    return {
        "True Adam": "True Adam",
        "Chad":      "Chad",
        "HHTN":      "HHTN",
        "HTN":       "High Tier Normie",
        "MTN":       "Mid Tier Normie",
        "LTN":       "Low Tier Normie",
    }.get(t, t)

def _top_pct(s):
    if s >= 9.0: return "1%"
    if s >= 8.0: return "5%"
    if s >= 7.5: return "15%"
    if s >= 6.0: return "40%"
    if s >= 4.5: return "70%"
    return "90%+"

def _level_str(s):
    if s >= 9.0: return "True Adam — Топ 1% мужчин"
    if s >= 8.0: return "Chad — Топ 5%"
    if s >= 7.5: return "HHTN — High High Tier Normie"
    if s >= 6.0: return "HTN — High Tier Normie"
    if s >= 4.5: return "MTN — Mid Tier Normie"
    return "LTN — Low Tier Normie"


def _para(c, text, x, y_top, w, h,
          font=None, size=10, color=None, align=TA_LEFT, leading=None):
    font = font or R
    color = color or WHITE_TXT
    leading = leading or round(size * 1.45)
    st = ParagraphStyle("p", fontName=font, fontSize=size, textColor=color,
                        leading=leading, alignment=align,
                        leftIndent=0, rightIndent=0, spaceBefore=0, spaceAfter=0)
    p = Paragraph(text, st)
    fr = Frame(x, _c(y_top + h), w, h, showBoundary=0,
               leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    fr.addFromList([p], c)


def _hline(c, x, y_top, w, color=LINE, lw=0.5):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(x, _c(y_top), x + w, _c(y_top))
    c.restoreState()


def _rect(c, x, y_top, w, h, fill=None, stroke=None, lw=0.5):
    c.saveState()
    if fill:   c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(lw)
    c.rect(x, _c(y_top + h), w, h,
           fill=1 if fill else 0,
           stroke=1 if stroke else 0)
    c.restoreState()


def _txt(c, text, x, y_top, font=None, size=10, color=None, align="left"):
    font = font or R
    color = color or WHITE_TXT
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(color)
    cy = _c(y_top)
    if align == "center": c.drawCentredString(x, cy, text)
    elif align == "right": c.drawRightString(x, cy, text)
    else: c.drawString(x, cy, text)
    c.restoreState()


def _footer(c, page_num, total, extra=""):
    c.saveState()
    c.setFont(R, 8)
    c.setFillColor(DIM)
    parts = [f"Telegram: {HANDLE}", f"{page_num} / {total}"]
    if extra: parts.insert(1, extra)
    c.drawCentredString(W / 2, MB / 2 + 2, "  ·  ".join(parts))
    c.restoreState()


def _header(c, title_extra=""):
    _rect(c, 0, 0, W, MT + 13*mm, fill=SURFACE)
    _txt(c, BOT, W / 2, MT + 5*mm, font=B, size=16, color=WHITE_TXT, align="center")
    sub = f"Telegram: {HANDLE}"
    if title_extra: sub = title_extra
    _txt(c, sub, W / 2, MT + 9.5*mm, font=R, size=9, color=DIM, align="center")
    _hline(c, 0, MT + 13*mm, W, color=LINE, lw=0.7)


def _draw_photo(c, image_bytes, x, y_top, max_w, max_h, circle=False):
    """Вставить фото в PDF."""
    if not image_bytes:
        return 0
    try:
        from reportlab.platypus import Image as RLImage
        pil = PILImage.open(io.BytesIO(image_bytes))
        iw, ih = pil.size
        scale = min(max_w / iw, max_h / ih)
        pw, ph = iw * scale, ih * scale
        px = x + (max_w - pw) / 2
        img = RLImage(io.BytesIO(image_bytes), width=pw, height=ph)
        img.drawOn(c, px, _c(y_top + ph))
        return ph
    except Exception:
        return 0


def _draw_radar(c, cx, cy, radius, scores, labels):
    """
    Рисует радарную диаграмму (паутина) прямо на canvas.
    cx, cy — центр в pt (canvas coords, y снизу).
    scores — список float 0–10.
    labels — список строк.
    """
    n = len(scores)
    if n < 3:
        return
    c.saveState()
    angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

    # Сетка
    for ring in [0.25, 0.5, 0.75, 1.0]:
        pts = [(cx + radius * ring * math.cos(a),
                cy + radius * ring * math.sin(a)) for a in angles]
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]:
            p.lineTo(*pt)
        p.close()
        c.drawPath(p)

    # Спицы
    for a in angles:
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(cx, cy, cx + radius * math.cos(a), cy + radius * math.sin(a))

    # Данные
    data_pts = [(cx + radius * (s / 10) * math.cos(a),
                 cy + radius * (s / 10) * math.sin(a))
                for s, a in zip(scores, angles)]
    c.setFillColor(colors.HexColor("#4A6CF730"))
    c.setStrokeColor(INFL_BD)
    c.setLineWidth(1.5)
    p = c.beginPath()
    p.moveTo(*data_pts[0])
    for pt in data_pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    # Точки
    c.setFillColor(INFL_BD)
    for pt in data_pts:
        c.circle(pt[0], pt[1], 3, fill=1, stroke=0)

    # Подписи
    c.setFont(R, 6.5)
    c.setFillColor(DIM)
    for i, (a, lbl) in enumerate(zip(angles, labels)):
        lx = cx + (radius + 12) * math.cos(a)
        ly = cy + (radius + 12) * math.sin(a)
        c.drawCentredString(lx, ly - 3, lbl)

    c.restoreState()


def _draw_bell(c, x, y_bottom, w, h, score):
    """
    Рисует упрощённую колоколообразную кривую нормального распределения
    и отмечает на ней позицию score.
    """
    c.saveState()
    # Фон
    _rect(c, x, y_bottom - h, w, h, fill=SURFACE)

    steps = 60
    pts = []
    for i in range(steps + 1):
        t = i / steps  # 0..1 → score 0..10
        z = (t * 10 - 5) / 1.8
        gauss = math.exp(-0.5 * z * z)
        px_i = x + t * w
        py_i = y_bottom - 4 - gauss * (h - 10)
        pts.append((px_i, _c(py_i)))

    c.setStrokeColor(DIM)
    c.setLineWidth(0.8)
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    c.drawPath(p)

    # Позиция игрока
    marker_x = x + (score / 10) * w
    c.setStrokeColor(_sc(score))
    c.setLineWidth(1.5)
    c.line(marker_x, _c(y_bottom - h + 4), marker_x, _c(y_bottom - 3))
    c.setFillColor(_sc(score))
    c.setFont(B, 7)
    c.drawCentredString(marker_x, _c(y_bottom - h + 2), f"{score:.1f}")

    # Ярлыки 1/5/10
    c.setFont(R, 6)
    c.setFillColor(DIM)
    c.drawCentredString(x + 4,          _c(y_bottom - 1), "1")
    c.drawCentredString(x + w / 2,      _c(y_bottom - 1), "5")
    c.drawCentredString(x + w - 4,      _c(y_bottom - 1), "10")

    c.restoreState()


def _draw_gauge(c, cx, cy, r, score):
    """
    Спидометр. cx,cy — центр в canvas coords (y снизу).
    Точки освещаются по дуге: 180° (левый край) → 0° (правый).
    score 0 = пусто, score 10 = вся дуга.
    """
    c.saveState()
    n_ticks = 36
    for i in range(n_ticks):
        t = i / (n_ticks - 1)          # 0 … 1
        angle = math.radians(180 - t * 180)   # 180° → 0°
        tx = cx + r * math.cos(angle)
        ty = cy + r * math.sin(angle)
        dot_r = r * 0.055
        tick_score = t * 10
        if tick_score <= score:
            col = _sc(tick_score)
        else:
            col = PANEL
        c.setFillColor(col)
        c.circle(tx, ty, dot_r, fill=1, stroke=0)

    # Игла
    needle_angle = math.radians(180 - score * 18)
    nx = cx + r * 0.68 * math.cos(needle_angle)
    ny = cy + r * 0.68 * math.sin(needle_angle)
    c.setStrokeColor(WHITE_TXT)
    c.setLineWidth(1.8)
    c.line(cx, cy, nx, ny)
    c.setFillColor(WHITE_TXT)
    c.circle(cx, cy, r * 0.06, fill=1, stroke=0)

    # Балл по центру
    c.setFont(B, r * 0.38)
    c.setFillColor(_sc(score))
    c.drawCentredString(cx, cy - r * 0.12, f"{score:.1f}")
    c.setFont(R, r * 0.17)
    c.setFillColor(DIM)
    c.drawCentredString(cx, cy - r * 0.30, "из 10")

    c.restoreState()


def _draw_comparison_bars(c, x, y_top, w, your_val, norm_val):
    """
    Два горизонтальных бара «Вы» vs «Норма».
    Метка — НАД баром, бар — под ней. Контрастные цвета.
    """
    if your_val is None or norm_val is None:
        return
    max_v = max(abs(float(your_val)), abs(float(norm_val)), 0.001)
    bar_h = 5
    bar_max_w = w
    label_gap = 4   # px между меткой и баром

    # — Ваш показатель
    _txt(c, f"Вы: {your_val}", x, y_top - 1, font=B, size=6.5, color=WHITE_TXT)
    bar_y = y_top + label_gap
    yw = bar_max_w * (abs(float(your_val)) / max_v)
    _rect(c, x, bar_y, bar_max_w, bar_h, fill=PANEL)
    _rect(c, x, bar_y, yw, bar_h, fill=INFL_BD)

    # — Норма Фаркаса
    y2 = bar_y + bar_h + 6
    _txt(c, f"Норма: {norm_val}", x, y2 - 1, font=B, size=6.5, color=DIM)
    bar_y2 = y2 + label_gap
    nw = bar_max_w * (abs(float(norm_val)) / max_v)
    _rect(c, x, bar_y2, bar_max_w, bar_h, fill=PANEL)
    _rect(c, x, bar_y2, nw, bar_h, fill=colors.HexColor("#555555"))


def _draw_percentile_strip(c, x, y_top, w, score):
    """
    Цветная полоса с маркером и подписью «Топ X%».
    """
    h = 9
    seg = w / 3
    _rect(c, x,           y_top, seg, h, fill=C_LOW)
    _rect(c, x + seg,     y_top, seg, h, fill=C_MID)
    _rect(c, x + 2 * seg, y_top, seg, h, fill=C_HIGH)

    # Маркер
    mx = x + (score / 10) * w
    c.saveState()
    c.setStrokeColor(WHITE_TXT)
    c.setLineWidth(2)
    c.line(mx, _c(y_top - 4), mx, _c(y_top + h + 4))
    c.restoreState()

    # Подписи шкалы
    _txt(c, "0",  x,         y_top + h + 5, font=R, size=6, color=DIM)
    _txt(c, "5",  x + w / 2, y_top + h + 5, font=R, size=6, color=DIM, align="center")
    _txt(c, "10", x + w,     y_top + h + 5, font=R, size=6, color=DIM, align="right")

    # Топ %
    top = _top_pct(score)
    _txt(c, f"Топ {top} мужчин", x + w / 2, y_top - 6,
         font=B, size=8, color=_sc(score), align="center")


# ── Данные метрик ─────────────────────────────────────────────────────────────
FARKAS_NORMS = {
    "symmetry":         ("Симметрия лица",            0.920,  None,   0.040),
    "face_proportions": ("Пропорции лица",            0.896,  "face_hw_ratio",   0.077),
    "vertical_balance": ("Вертикальный баланс",       0.728,  "vert_balance",    0.110),
    "cheekbones":       ("Баланс скул и челюсти",     1.356,  "cheek_jaw_ratio", 0.209),
    "eyes":             ("Размер глаз",               0.223,  "eye_to_face",     0.040),
    "eye_distance":     ("Расстояние между глазами",  0.271,  "inner_eye_to_face", 0.048),
    "canthal_tilt":     ("Наклон глаз",               0.036,  "canthal_norm",    0.055),
    "nose":             ("Ширина носа",               0.234,  "nose_to_face",    0.046),
    "lips":             ("Ширина рта",                0.403,  "mouth_to_face",   0.062),
    "nose_length":      ("Длина носа",                0.421,  "nose_len_ratio",  0.112),
    "chin_length":      ("Длина подбородка",          0.283,  "chin_len_ratio",  0.060),
    "chin_contour":     ("Контур подбородка",         0.630,  "chin_contour",    0.132),
    "nose_to_mouth":    ("Нос к ширине рта",          0.583,  "nose_to_mouth",   0.092),
    "biocular":         ("Биокулярная ширина",        0.713,  "biocular_width",  0.110),
    "forehead":         ("Ширина лба",                0.919,  "forehead_ratio",  0.121),
    "lip_fullness":     ("Полнота губ",               0.347,  "lip_fullness",    0.062),
    "lip_ratio":        ("Пропорции губ",             0.639,  "lip_ratio",       0.143),
    "jaw_to_mouth":     ("Челюсть к ширине рта",      1.810,  "jaw_to_mouth",    0.308),
    "eye_shape":        ("Форма глаз",                0.285,  "eye_shape",       0.055),
    "brow_height":      ("Высота бровей",             0.063,  "brow_dist_ratio", 0.026),
    "jaw_angle":        ("Угол нижней челюсти",       125.0,  "jaw_angle_deg",   12.0),
}

# Описания направлений для генерации текста
_METRIC_DIRECTIONS = {
    "symmetry_score":          "both",
    "face_proportions_score":  "up",
    "vertical_balance_score":  "down",
    "cheekbones_score":        "down",
    "eyes_score":              "both",
    "eye_distance_score":      "both",
    "canthal_tilt_score":      "up",
    "nose_score":              "down",
    "lips_score":              "both",
    "nose_length_score":       "both",
    "chin_length_score":       "both",
    "chin_contour_score":      "down",
    "nose_to_mouth_score":     "both",
    "biocular_score":          "both",
    "forehead_score":          "up",
    "lip_fullness_score":      "both",
    "lip_ratio_score":         "both",
    "jaw_to_mouth_score":      "up",
    "eye_shape_score":         "both",
    "brow_height_score":       "both",
    "jaw_angle_score":         "down",
}

# Что означает отклонение вверх/вниз для каждой метрики
_DEVIATION_MEANING = {
    "symmetry_score":          ("высокая симметрия", "асимметрия"),
    "face_proportions_score":  ("удлинённое, мужественное лицо", "более компактная форма лица"),
    "vertical_balance_score":  ("более длинная нижняя треть, волевой характер", "более длинная средняя треть"),
    "cheekbones_score":        ("выраженные скулы относительно челюсти", "широкая челюсть относительно скул"),
    "eyes_score":              ("более крупные глаза относительно лица", "более компактные глаза"),
    "eye_distance_score":      ("широкая посадка глаз", "близкая посадка глаз"),
    "canthal_tilt_score":      ("позитивный кантальный тильт, hunter eyes", "нейтральный или негативный наклон"),
    "nose_score":              ("аккуратный, узкий нос", "более широкий нос"),
    "lips_score":              ("широкий рот", "компактный рот"),
    "nose_length_score":       ("длинная средняя треть", "короткий нос"),
    "chin_length_score":       ("выраженный, длинный подбородок", "менее выраженный подбородок"),
    "chin_contour_score":      ("заострённый V-подбородок", "более квадратный подбородок"),
    "nose_to_mouth_score":     ("нос шире относительно рта", "нос уже относительно рта"),
    "biocular_score":          ("широкий разрез глаз", "узкий разрез глаз"),
    "forehead_score":          ("широкий, доминантный лоб", "узкий лоб"),
    "lip_fullness_score":      ("более полные губы", "более тонкие губы"),
    "lip_ratio_score":         ("верхняя губа шире нижней", "нижняя губа полнее верхней"),
    "jaw_to_mouth_score":      ("широкая челюсть относительно рта", "узкая челюсть"),
    "eye_shape_score":         ("более круглые глаза", "вытянутые горизонтально, хищный разрез"),
    "brow_height_score":       ("высокие брови", "низкие, нависающие брови"),
    "jaw_angle_score":         ("острый gonial angle — угловатая, мужественная челюсть", "тупой угол — мягкая, менее выраженная челюсть"),
}


def _build_sigma_text(field, your_val, norm_val, std, score):
    """
    Генерирует текст: «Твоё значение — X при норме Y, отклонение ~Zσ направление, что означает...»
    Возвращает строку или пустую строку если данных нет.
    """
    if your_val is None or norm_val is None or std is None or std == 0:
        return ""
    sigma = abs(your_val - norm_val) / std
    direction_up = your_val > norm_val
    direction_str = "вверх" if direction_up else "вниз"
    meaning_up, meaning_down = _DEVIATION_MEANING.get(field, ("выше нормы", "ниже нормы"))
    meaning = meaning_up if direction_up else meaning_down
    yv = round(your_val, 3)
    nv = round(norm_val, 3)
    return (
        f"Твоё значение — {yv} при норме {nv}, "
        f"отклонение ~{sigma:.1f}\u03c3 {direction_str}, "
        f"что соответствует: {meaning}."
    )


def _build_dynamic_body(field, base_text, your_val, norm_val, std, score):
    """Собирает финальный текст страницы метрики с реальными значениями."""
    sigma_line = _build_sigma_text(field, your_val, norm_val, std, score)
    if sigma_line:
        return f"{base_text}\n\n{sigma_line}"
    return base_text

METRICS_20 = [
    ("symmetry_score",        "symmetry",
     "Метрика оценивает, насколько зеркально совпадают левая и правая стороны лица по "
     "ключевым парам контрольных точек. Отклонение считается как средняя разница расстояний "
     "от центральной оси до симметричных пар точек. Даже наибольшее отклонение в пределах "
     "нормы, как правило, незаметно невооружённым глазом и свидетельствует о генетическом здоровье.",
     "Симметрия лица: насколько левая и правая стороны зеркальны",
     "Высокая симметрия создаёт ощущение гармонии при первом взгляде на лицо. "
     "Это одна из ключевых основ привлекательности, воспринимаемая как маркер биологического качества."),

    ("face_proportions_score","face_proportions",
     "Метрика измеряет отношение высоты лица (от переносицы до подбородка) к ширине скул. "
     "Твоё значение сравнивается с антропометрической нормой Фаркаса. "
     "Лица с соотношением, близким к медиане, оцениваются как наиболее привлекательные.",
     "Высота лица / ширина скул",
     "Гармоничная форма лица обеспечивает нейтральный, приятный фон для остальных черт. "
     "Ни одна зона не перетягивает внимание, что позволяет выразительным глазам и скулам доминировать."),

    ("vertical_balance_score","vertical_balance",
     "Метрика сравнивает среднюю треть лица (переносица → основание носа) с нижней третью "
     "(нос → подбородок). Отклонение от нормы вниз означает более длинную нижнюю часть, "
     "что придаёт лицу волевой характер. Отклонение вверх — более длинную среднюю часть.",
     "Средняя треть лица / нижняя треть лица",
     "Выраженная нижняя треть усиливает восприятие уверенности и зрелости. "
     "В сочетании с острыми скулами это формирует цельный мужественный образ."),

    ("cheekbones_score",      "cheekbones",
     "Метрика измеряет отношение ширины скул к ширине челюсти. Высокое значение означает "
     "более выраженные скулы относительно линии челюсти. Это создаёт резкий контурный рельеф "
     "— так называемые chiseled cheekbones, один из ключевых маркеров маскулинности.",
     "Ширина скул / ширина челюсти",
     "Выраженные скулы ассоциируются с высоким уровнем тестостерона и воспринимаются как "
     "сигнал генетического качества. Этот рельеф формирует запоминающийся силуэт."),

    ("eyes_score",            "eyes",
     "Метрика оценивает размер глаз относительно ширины лица. "
     "Оптимальный размер глаз обеспечивает баланс между выразительностью и пропорциональностью. "
     "Отклонения в обе стороны влияют на восприятие взгляда.",
     "Ширина глаза / ширина лица",
     "Размер глаз — один из главных факторов выразительности взгляда. "
     "Пропорциональные глаза создают гармоничный баланс и усиливают первое впечатление."),

    ("eye_distance_score",    "eye_distance",
     "Метрика измеряет расстояние между внутренними углами глаз относительно ширины лица. "
     "Норма по Фаркасу — около 0.271. Слишком близкие или далёкие глаза нарушают гармонию "
     "средней трети лица и влияют на восприятие взгляда.",
     "Расстояние между внутренними углами глаз / ширина лица",
     "Правильная постановка глаз создаёт ощущение баланса. "
     "Широкая постановка воспринимается как открытость, узкая — снижает доминантность взгляда."),

    ("canthal_tilt_score",    "canthal_tilt",
     "Кантальный тильт — угол наклона глазной щели. Положительный тильт (внешний угол выше "
     "внутреннего) соответствует так называемому хищному взгляду (hunter eyes) и ассоциируется "
     "с доминантностью и привлекательностью. Отрицательный тильт создаёт мягкий, более нейтральный взгляд.",
     "Угол наклона глазной щели (hunter eyes)",
     "Положительный кантальный тильт — один из наиболее заметных маркеров мужской привлекательности. "
     "Он формирует хищный, уверенный взгляд, который воспринимается как доминантность."),

    ("nose_score",            "nose",
     "Метрика оценивает ширину носа относительно ширины лица. "
     "Нос в пределах нормы гармонично вписывается в пропорции лица и не привлекает "
     "лишнего внимания. Отклонения влияют на баланс центральной зоны лица.",
     "Ширина носа / ширина лица",
     "Пропорциональный нос удерживает баланс средней зоны. "
     "Слишком широкий нос перетягивает взгляд; слишком узкий — нарушает пропорции."),

    ("lips_score",            "lips",
     "Метрика оценивает ширину рта относительно ширины лица. "
     "Оптимальный рот обрамляет нижнюю треть лица и создаёт гармонию между носом и подбородком. "
     "Норма Фаркаса — около 0.403.",
     "Ширина рта / ширина лица",
     "Пропорциональный рот завершает гармонию нижней трети и усиливает выразительность лица. "
     "Этот параметр напрямую влияет на восприятие губ и привлекательность улыбки."),

    ("nose_length_score",     "nose_length",
     "Метрика измеряет длину носа (от переносицы до основания) относительно общей высоты лица. "
     "Нос правильной длины поддерживает баланс трёх третей. Длинный нос визуально удлиняет "
     "среднюю треть; короткий — делает лицо более плоским.",
     "Длина носа / высота лица",
     "Длина носа определяет визуальный вес средней трети лица. "
     "Пропорциональный нос незаметен — внимание направляется на глаза и общий контур."),

    ("chin_length_score",     "chin_length",
     "Метрика оценивает высоту нижней части подбородка (от нижней губы до кончика подбородка) "
     "относительно высоты лица. Выраженный подбородок придаёт лицу завершённость и "
     "мужественность. Норма Фаркаса — около 0.283.",
     "Высота подбородка / высота лица",
     "Выраженный подбородок — маркер зрелости и мужественности. "
     "Вместе с длиной нижней трети он формирует волевой, решительный образ."),

    ("chin_contour_score",    "chin_contour",
     "Метрика измеряет степень сужения подбородка: отношение ширины самой узкой части "
     "подбородочной зоны к ширине челюсти. Высокое значение означает более прямой, "
     "квадратный подбородок; низкое — выраженно сужающийся к точке подбородок.",
     "Ширина сужения подбородка / ширина челюсти",
     "Контур подбородка влияет на силуэт нижней трети. "
     "Квадратный подбородок придаёт мужественность; заострённый — элегантность."),

    ("nose_to_mouth_score",   "nose_to_mouth",
     "Метрика оценивает соотношение ширины носа к ширине рта. "
     "Это пропорция, которую Фаркас считает одним из ключевых показателей гармонии "
     "центральной зоны лица. Значение около 0.583 создаёт визуально сбалансированную нижнюю треть.",
     "Ширина носа / ширина рта",
     "Баланс носа и рта определяет гармонию центральной оси лица. "
     "Нарушение этой пропорции привлекает внимание к одному из элементов в ущерб другому."),

    ("biocular_score",        "biocular",
     "Биокулярная ширина — расстояние между внешними углами глаз относительно ширины лица. "
     "Норма по Фаркасу — около 0.713. Этот параметр определяет визуальную ширину зоны глаз "
     "и влияет на то, насколько открытым и выразительным воспринимается взгляд.",
     "Расстояние между внешними углами глаз / ширина лица",
     "Биокулярная ширина определяет «масштаб» глаз на лице. "
     "Оптимальное значение обеспечивает выразительный взгляд без ощущения перегруженности."),

    ("forehead_score",        "forehead",
     "Метрика оценивает ширину лба (в области висков) относительно ширины скул. "
     "Норма около 0.919 означает, что лоб чуть уже скул, что характерно для мужского "
     "инвертированного треугольника — одного из самых привлекательных контуров лица.",
     "Ширина лба / ширина скул",
     "Широкий лоб создаёт доминантный, уверенный силуэт. "
     "В сочетании с узкой челюстью он формирует V-образный мужской контур лица."),

    ("lip_fullness_score",    "lip_fullness",
     "Метрика оценивает объём губ: суммарная высота верхней и нижней губы относительно "
     "ширины рта. Норма Фаркаса — около 0.347. Более высокое значение означает более "
     "полные, объёмные губы, что воспринимается как признак молодости.",
     "Высота губ / ширина рта",
     "Полные губы — один из универсальных маркеров молодости и привлекательности. "
     "Они усиливают выразительность нижней трети и придают лицу чувственность."),

    ("lip_ratio_score",       "lip_ratio",
     "Метрика оценивает пропорцию между верхней и нижней губой. "
     "Норма Фаркаса — около 0.639, то есть нижняя губа немного полнее верхней. "
     "Это соотношение создаёт ощущение природной гармонии без искусственности.",
     "Высота верхней губы / высота нижней губы",
     "Правильная пропорция губ создаёт естественный, привлекательный контур рта. "
     "Нарушение баланса может визуально деформировать улыбку и выражение лица."),

    ("jaw_to_mouth_score",    "jaw_to_mouth",
     "Метрика измеряет соотношение ширины челюсти к ширине рта. "
     "Норма около 1.810 означает, что челюсть примерно в 1.8 раза шире рта. "
     "Это определяет, насколько чётко рот вписывается в контур нижней трети.",
     "Ширина челюсти / ширина рта",
     "Широкая челюсть создаёт мужественный, структурный вид. "
     "Правильное соотношение с шириной рта обеспечивает баланс нижней трети и чёткость контура."),

    ("eye_shape_score",       "eye_shape",
     "Метрика оценивает форму глаза: отношение высоты к ширине. "
     "Норма по Фаркасу — около 0.285. Более высокое значение означает миндалевидные глаза, "
     "более низкое — горизонтально вытянутые, часто ассоциирующиеся с хищным взглядом.",
     "Высота глаза / ширина глаза",
     "Форма глаза определяет характер взгляда: миндалевидные глаза воспринимаются как "
     "выразительные; вытянутые горизонтально — как хищные и доминантные."),

    ("brow_height_score",     "brow_height",
     "Метрика оценивает расстояние между бровью и верхним веком относительно высоты лица. "
     "Норма Фаркаса — около 0.063. Правильная высота бровей создаёт гармонию, брови "
     "естественно и гармонично дополняют зону глаз.",
     "Расстояние бровь–глаз / высота лица",
     "Правильная высота бровей обрамляет глаза и акцентирует взгляд. "
     "Слишком высокие брови придают удивлённый вид; слишком низкие — хмурый."),

    ("jaw_angle_score",       "jaw_angle",
     "Gonial angle (угол нижней челюсти) — угол в точке угла нижней челюсти между "
     "ветвью (ramus, уходящей вверх к уху) и телом (body, уходящим к подбородку). "
     "Измеряется в градусах. Норма для мужчин: ~125°. Острый угол формирует "
     "угловатую, структурную челюсть. Тупой угол (~145°+) — мягкую, менее выраженную.",
     "Gonial angle (угол в точке угла нижней челюсти, в градусах)",
     "Острый gonial angle — один из главных маркеров мужественности. "
     "Он создаёт чёткий контур лица, ассоциирующийся с тестостероном и доминантностью. "
     "Широкий угол сглаживает форму нижней трети и снижает резкость профиля."),
]

METRIC_ORDER_FULL = [
    ("symmetry_score",         "Симметрия лица",           1),
    ("face_proportions_score", "Пропорции лица",           2),
    ("vertical_balance_score", "Вертикальный баланс",      3),
    ("cheekbones_score",       "Баланс скул и челюсти",    4),
    ("eyes_score",             "Размер глаз",              5),
    ("eye_distance_score",     "Расстояние между глазами", 6),
    ("canthal_tilt_score",     "Наклон глаз",              7),
    ("nose_score",             "Ширина носа",              8),
    ("lips_score",             "Ширина рта",               9),
    ("nose_length_score",      "Длина носа",               10),
    ("chin_length_score",      "Длина подбородка",         11),
    ("chin_contour_score",     "Контур подбородка",        12),
    ("nose_to_mouth_score",    "Нос к ширине рта",         13),
    ("biocular_score",         "Биокулярная ширина",       14),
    ("forehead_score",         "Ширина лба",               15),
    ("lip_fullness_score",     "Полнота губ",              16),
    ("lip_ratio_score",        "Пропорции губ",            17),
    ("jaw_to_mouth_score",     "Челюсть к ширине рта",     18),
    ("eye_shape_score",        "Форма глаз",               19),
    ("brow_height_score",      "Высота бровей",            20),
    ("jaw_angle_score",        "Угол нижней челюсти",      21),
]

BRIEF_GRID = [
    ("symmetry_score",        "Симметрия",          "Зеркальность левой и правой сторон"),
    ("vertical_balance_score","Вертикальный баланс","Средняя vs нижняя треть лица"),
    ("cheekbones_score",      "Скулы / челюсть",    "Ширина скул к ширине челюсти"),
    ("eyes_score",            "Размер глаз",        "Ширина глаза к ширине лица"),
    ("canthal_tilt_score",    "Наклон глаз",        "Кантальный тильт — hunter eyes"),
    ("nose_score",            "Ширина носа",        "Ширина носа к ширине лица"),
    ("lip_fullness_score",    "Полнота губ",        "Объём губ к ширине рта"),
    ("chin_contour_score",    "Контур челюсти",     "Сужение подбородка к линии челюсти"),
    ("brow_height_score",     "Высота бровей",      "Расстояние от брови до глаза"),
]

# Советы по слабым метрикам (обновлённые — мужской уклон)
METRIC_ADVICE = {
    "symmetry_score":
        "Жуй с обеих сторон поровну. Брекеты / ретейнер исправляют прикус — главную причину "
        "асимметрии. Спи на спине. Исключи постоянный упор щеки в руку. "
        "Регулярные упражнения мьюинга выравнивают давление на скуловую кость.",
    "face_proportions_score":
        "Причёска корректирует форму: высокий объём вверху визуально удлиняет лицо, "
        "объём по бокам расширяет. Подбери фасон под целевые пропорции. "
        "Снижение % жира до 10–13% делает контуры чётче и лицо визуально уже.",
    "vertical_balance_score":
        "Коррекция — задача стилиста и парикмахера. Чёлка укорачивает верхнюю треть. "
        "Короткая борода или щетина подчёркивает нижнюю треть. "
        "Мьюинг со временем смещает структуры лица. Работай системно — эффект через 6–18 мес.",
    "cheekbones_score":
        "Снижай % жира в теле ниже 13% — скулы проявятся автоматически. "
        "Мьюинг: язык в нёбо — стимулирует рост скулового выступа. "
        "Жвачка Falim ежедневно по 20 минут нагружает жевательные мышцы. "
        "Подстриженные виски визуально подчёркивают скуловой рельеф.",
    "jaw_angle_score":
        "Gonial angle (угол нижней челюсти) — ключевой маркер мужественности. "
        "Острый угол (~120°) = чёткая угловатая челюсть. Тупой (~145°+) = «мягкая» челюсть. "
        "Жвачка Falim 2–3 раза в день по 20 минут развивает massa/masseter — делает угол визуально острее. "
        "Боковая борода / fade на висках зрительно подчёркивают угол челюсти. "
        "Долгосрочно: мьюинг + снижение жира до 10% раскрывают структуру. "
        "Хирургически: угловые имплантаты нижней челюсти или гониопластика.",
    "eyes_score":
        "Убирай отёки: ледяной компресс 5 мин утром или нефритовый роллер от носа к вискам. "
        "Ограничь соль, алкоголь, сахар — главные причины отёчности лица. "
        "Сон 8 ч. Ретинол 0.025% снижает пигментацию вокруг глаз. "
        "Дренажный массаж нижнего века убирает постоянную припухлость.",
    "eye_distance_score":
        "Близкая постановка: объём по бокам причёски, светлые акценты у внешних углов бровей. "
        "Далёкая постановка: чёрные акценты у внутренних углов, высокая переносица в кадре. "
        "Форма и заполненность бровей визуально меняет воспринимаемое расстояние.",
    "canthal_tilt_score":
        "Убери отёки нижнего века (ледяной роллер, сон, отказ от соли). "
        "Мьюинг поднимает среднюю зону лица — натягивает кожу под глазом вверх. "
        "Гримасы «hunter eyes» (лёгкое прищуривание без сморщивания лба) тренируют мышцу. "
        "Гречаная подушка-валик снижает отёки во сне.",
    "nose_score":
        "Объём на висках визуально уменьшает нос относительно лица. "
        "Стрижка с широкой верхней частью (андеркат, fade) сужает восприятие центральной зоны. "
        "Умеренный конторинг носа (минималистичный хайлайт по спинке) доступен каждому мужчине.",
    "lips_score":
        "Постоянное увлажнение бальзамом делает губы визуально полнее. "
        "Нежный скраб из сахара + кокосового масла раз в неделю. "
        "Отказ от курения и алкоголя: цвет губ восстанавливается через 2–4 недели.",
    "nose_length_score":
        "Длинный нос: объём причёски вверху, высокая причёска переводит акцент на верхнюю треть. "
        "Короткий нос: тёмный цвет бороды и наращивание нижней трети.",
    "chin_length_score":
        "Борода на подбородке (goatee) + короткие виски визуально удлиняет нижнюю треть. "
        "Мьюинг и правильное положение языка со временем выдвигают подбородок вперёд. "
        "Снижение % жира делает подбородок визуально более выраженным.",
    "chin_contour_score":
        "Снизь % жира — чёткость подбородочного контура улучшится первой. "
        "Мьюинг и жвачка Falim укрепляют подбородочную область. "
        "Чёткие края стрижки и виски создают оптический контраст с контуром.",
    "nose_to_mouth_score":
        "Баланс носа и рта визуально корректируется работой с бровями: "
        "пышные брови уводят акцент вверх от носа. "
        "Небольшая борода под нижней губой смещает восприятие центра вниз.",
    "biocular_score":
        "Биокулярная ширина — костная характеристика. "
        "Корректируется правильной формой бровей (удлинение в стороны) и "
        "объёмом причёски у висков — создаёт зрительно более широкий взгляд.",
    "forehead_score":
        "Лоб оценивается в гармонии с остальными чертами лица — сильная челюсть и скулы "
        "могут сделать любую ширину лба привлекательной, если сохраняются общие пропорции. "
        "Широкий лоб балансируется плавной чёлкой или объёмом чуть ниже линии роста волос. "
        "Узкий лоб визуально расширяется объёмом у висков и отсутствием чёлки. "
        "Правильная линия роста волос создаёт оптимальный силуэт под твой тип лица.",
    "lip_fullness_score":
        "Умеренный объём губ — плюс к гармонии. Очень тонкие губы снижают баланс лица. "
        "Ежедневное увлажнение бальзамом делает губы визуально полнее. "
        "Ледяной кубик по губам усиливает кровообращение — временно прибавляет объём. "
        "Нежный скраб из сахара раз в неделю улучшает текстуру. "
        "Отказ от курения: через 30 дней объём и цвет губ заметно восстанавливаются.",
    "lip_ratio_score":
        "Пропорции губ — одна из наименее поддающихся коррекции метрик без процедур. "
        "Увлажняй губы ежедневно. Тонкие усы под носом визуально изменяют воспринимаемый размер верхней губы.",
    "jaw_to_mouth_score":
        "Чёткость линии челюсти улучшается при снижении % жира и правильном прикусе. "
        "Мьюинг укрепляет жевательную мышцу — добавляет ширину внизу. "
        "Жвачка Falim 20 минут ежедневно — долгосрочный инструмент.",
    "eye_shape_score":
        "Горизонтально вытянутые глаза воспринимаются как более хищные — это плюс. "
        "Убери отёчность верхнего века для более чёткого разреза: ледяной компресс утром, "
        "антигистамины при аллергии, ретинол при пигментации.",
    "brow_height_score":
        "Небольшое расстояние между бровями и глазами считается более привлекательным — "
        "придаёт взгляду глубину и выразительность. "
        "Если расстояние заметно большое: не выщипывай брови снизу — это только увеличивает разрыв. "
        "Наоборот, слегка опусти хвост брови; нависающий объём причёски со лба визуально "
        "сокращает верхнюю зону. Лёгкое прищуривание ('hunter eyes') при взгляде "
        "практически устраняет большой brow-eye gap в восприятии окружающих.",
}


# ─────────────────────────────────────────────────────────────────────────────
# КРАТКИЙ РАЗБОР  (2 страницы)
# ─────────────────────────────────────────────────────────────────────────────

def generate_brief_pdf(metrics: FaceMetrics, name: str = "") -> bytes:
    buf = io.BytesIO()
    c = pdfgen_canvas.Canvas(buf, pagesize=A4)

    # ── Страница 1 ────────────────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)

    y = MT + 16*mm

    # ── Фото (если есть landmark_image) ──────────────────────────────────────
    photo_h_used = 0
    if metrics.landmark_image:
        ph = _draw_photo(c, metrics.landmark_image, ML, y, BW, 72*mm)
        if ph:
            # Рамка вокруг фото
            _rect(c, ML + (BW - min(BW, ph * BW / 72*mm)) / 2 - 1, y - 1,
                  min(BW, BW) + 2, ph + 2, stroke=LINE, lw=0.8)
            photo_h_used = ph + 4*mm

    y += photo_h_used

    # Большой балл
    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 14*mm,
         font=B, size=36, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 14*mm, font=R, size=13, color=DIM, align="left")

    tier_str = f"{metrics.tier}  ·  {_tier_label(metrics.tier)}"
    y += 20*mm
    _txt(c, tier_str, W / 2, y, font=B, size=10, color=WHITE_TXT, align="center")
    y += 5*mm
    top = _top_pct(metrics.overall_score)
    _txt(c, f"Ты в топ {top} по геометрии лица", W / 2, y, font=R, size=9, color=DIM, align="center")
    y += 5*mm
    _hline(c, ML, y, BW)

    # 3×3 сетка
    y += 4*mm
    card_w = (BW - 2 * 4*mm) / 3
    card_h = 42*mm
    row_gap = 3*mm

    for row in range(3):
        for col in range(3):
            idx = row * 3 + col
            field, label, desc = BRIEF_GRID[idx]
            score = getattr(metrics, field, 5.0)
            sc_col = _sc(score)
            lv = _lv(score)

            cx = ML + col * (card_w + 4*mm)
            cy = y + row * (card_h + row_gap)

            _rect(c, cx, cy, card_w, card_h, fill=CARD, stroke=LINE, lw=0.5)

            _para(c, label, cx + 3, cy + 4, card_w - 6, 10,
                  font=B, size=8, color=WHITE_TXT, align=TA_CENTER)

            bar_w = (card_w - 10) * score / 10
            _rect(c, cx + 5, cy + 15, card_w - 10, 3, fill=SURFACE)
            _rect(c, cx + 5, cy + 15, bar_w, 3, fill=sc_col)

            _txt(c, f"{score:.2f}", cx + card_w / 2, cy + 23*mm,
                 font=B, size=20, color=sc_col, align="center")
            _txt(c, lv, cx + card_w / 2, cy + 29*mm,
                 font=R, size=7.5, color=sc_col, align="center")

            # Описание метрики под уровнем
            _para(c, desc, cx + 3, cy + 32*mm, card_w - 6, 9,
                  font=R, size=6.5, color=DIM, align=TA_CENTER)

    _footer(c, 1, 2)
    c.showPage()

    # ── Страница 2 — Апселл ───────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)

    y = MT + 14*mm
    _txt(c, "Это — только верхушка айсберга.", ML, y, font=B, size=13, color=WHITE_TXT)
    y += 7*mm
    _para(c,
          "Краткий разбор показывает лишь 9 из 20 метрик твоего лица и не раскрывает, "
          "что именно снижает привлекательность и как это исправить конкретными шагами.",
          ML, y, BW, 16, font=R, size=9.5, color=DIM)
    y += 18*mm

    # Визуальный блок: "9 метрик из 20"
    bar_total_w = BW
    bar_h = 11*mm
    _rect(c, ML, y, bar_total_w, bar_h, fill=PANEL)
    filled_w = bar_total_w * 9 / 20
    _rect(c, ML, y, filled_w, bar_h, fill=INFL_BD)
    _txt(c, "9 из 20 метрик  (45%)", ML + 4, y + 7.5*mm, font=B, size=8, color=WHITE_TXT)
    _txt(c, "Краткий разбор", ML + 4, y + 3.5*mm, font=R, size=7, color=DIM)
    _txt(c, "Полный разбор — все 20 метрик", ML + bar_total_w - 4, y + 5.5*mm,
         font=B, size=8, color=GOLD, align="right")
    y += bar_h + 6*mm

    _hline(c, ML, y, BW, color=LINE)
    y += 5*mm
    _txt(c, "Полный разбор (25 страниц) включает:", ML, y, font=B, size=10.5, color=GOLD)
    y += 7*mm

    full_bullets = [
        ("◉  Все 20 метрик с подробным разбором",
         "Для каждой зоны лица — твой точный показатель, норма Фаркаса, отклонение в σ, "
         "детальное описание и как эта метрика влияет на восприятие тебя окружающими."),
        ("◉  Конкретные способы улучшить внешность",
         "Свыше 40 персонализированных рекомендаций: мьюинг, уход за кожей, причёска, "
         "борода, питание, сон, контуринг скул, упражнения — "
         "всё конкретно под твои слабые метрики."),
        ("◉  Стиль и уход: практические шаги",
         "Подборка методик (брови, SPF, ретинол, жвачка Falim, ледяные компрессы) "
         "с пояснением когда ожидать результат и реальные референсы."),
        ("◉  Диаграммы и графики",
         "Радарный профиль твоих 20 метрик, позиция на кривой нормального распределения, "
         "таблица сравнения твоих показателей с нормой Фаркаса."),
    ]

    for btitle, btext in full_bullets:
        block_h = 22*mm
        _rect(c, ML, y, BW, block_h, fill=SURFACE, stroke=LINE, lw=0.4)
        _rect(c, ML, y, 4, block_h, fill=INFL_BD)
        _txt(c, btitle, ML + 10, y + 5.5*mm, font=B, size=9, color=WHITE_TXT)
        _para(c, btext, ML + 10, y + 8*mm, BW - 14, block_h - 10*mm,
              font=R, size=8.5, color=DIM, align=TA_JUSTIFY)
        y += block_h + 3*mm

    y += 3*mm

    # Мини-превью скрытых метрик
    _txt(c, "Скрытые метрики (недоступны в кратком разборе):", ML, y,
         font=B, size=9, color=DIM)
    y += 5*mm
    hidden = [
        ("Вертикальный баланс", "Длина носа", "Длина подбородка", "Биокулярная ширина",
         "Ширина лба", "Форма глаз", "Пропорции губ", "Полнота губ",
         "Челюсть к ширине рта", "Нос к ширине рта", "Контур подбородка"),
    ]
    cols = 3
    col_w_h = (BW - (cols - 1) * 2*mm) / cols
    items = hidden[0]
    for i, item in enumerate(items):
        col = i % cols
        row = i // cols
        ix = ML + col * (col_w_h + 2*mm)
        iy = y + row * 6.5*mm
        _rect(c, ix, iy, col_w_h, 5.5*mm, fill=PANEL)
        _txt(c, f"? {item}", ix + 3, iy + 3.8*mm, font=R, size=7, color=DIM)
    rows_count = math.ceil(len(items) / cols)
    y += rows_count * 6.5*mm + 5*mm

    # CTA кнопка
    btn_h = 14*mm
    _rect(c, ML, y, BW, btn_h, fill=INFL_BD)
    _txt(c, "Получить полный разбор  →",
         W / 2, y + btn_h / 2 + 2*mm, font=B, size=12, color=WHITE_TXT, align="center")

    _footer(c, 2, 2)
    c.showPage()
    c.save()
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# ПОЛНЫЙ РАЗБОР  (25 страниц)
# ─────────────────────────────────────────────────────────────────────────────

def _get_score(metrics, field):
    return getattr(metrics, field, 5.0)


def _get_raw(metrics, detail_key):
    if detail_key is None:
        return None
    return metrics.details.get(detail_key)


def _draw_score_bar(c, x, y_top, w, h, score):
    bar_h = 7
    bar_y = y_top + h / 2 - bar_h / 2
    _rect(c, x, bar_y, w, bar_h, fill=PANEL)
    fill_w = w * score / 10
    _rect(c, x, bar_y, fill_w, bar_h, fill=_sc(score))
    norm_x = x + w * 0.5
    c.saveState()
    c.setStrokeColor(DIM)
    c.setLineWidth(1)
    c.line(norm_x, _c(bar_y - 2), norm_x, _c(bar_y + bar_h + 2))
    c.restoreState()
    _txt(c, f"{score:.2f}/10", x + w / 2, bar_y - 6, font=B, size=12,
         color=_sc(score), align="center")


def _full_cover(c, metrics):
    """Страница 1 — обложка с фото."""
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)

    y = MT + 16*mm
    _para(c, "Полный математический разбор геометрии твоего лица.",
          ML, y, BW, 14, font=R, size=11, color=DIM, align=TA_CENTER)
    y += 14

    # Фото
    photo_h = 100*mm
    if metrics.landmark_image:
        ph = _draw_photo(c, metrics.landmark_image, ML, y, BW, photo_h)
        if ph:
            _rect(c, ML + (BW - ph * (BW / photo_h)) / 2 - 1, y - 1,
                  ph * (BW / photo_h) + 2, ph + 2, stroke=INFL_BD, lw=1.2)
            y += ph + 5*mm
        else:
            y += photo_h + 5*mm
    else:
        y += photo_h + 5*mm

    # Балл
    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 14*mm,
         font=B, size=36, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 14*mm, font=R, size=13, color=DIM, align="left")
    y += 20*mm

    top = _top_pct(metrics.overall_score)
    _para(c, f"Ты входишь в топ {top} людей по геометрии лица!",
          ML, y, BW, 14, font=B, size=13, color=WHITE_TXT, align=TA_CENTER)
    y += 15*mm

    _txt(c, f"Уровень: {_level_str(metrics.overall_score)}", W / 2, y,
         font=R, size=10, color=DIM, align="center")
    y += 7*mm

    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    strong_3 = sorted_asc[-3:][::-1]
    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}
    strong_str = ", ".join(name_map[f].lower() for f, _ in strong_3)
    _txt(c, f"Сильные стороны: {strong_str}", W / 2, y,
         font=R, size=9, color=DIM, align="center")

    _footer(c, 1, 25)


def _full_overview(c, metrics):
    """Страница 2 — сводный обзор с радарной диаграммой."""
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)

    y = MT + 14*mm

    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 12*mm,
         font=B, size=34, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 12*mm, font=R, size=12, color=DIM, align="left")
    y += 18*mm

    top = _top_pct(metrics.overall_score)
    _para(c, f"Ты входишь в топ {top} людей по геометрии лица!",
          ML, y, BW, 12, font=B, size=11, color=WHITE_TXT, align=TA_CENTER)
    y += 13*mm

    _txt(c, f"Уровень: {_level_str(metrics.overall_score)}", W / 2, y,
         font=R, size=10, color=DIM, align="center")
    y += 6*mm

    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    weak_3 = sorted_asc[:3]
    strong_3 = sorted_asc[-3:][::-1]
    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}

    strong_str = ", ".join(name_map[f].lower() for f, _ in strong_3)
    _txt(c, f"Сильные стороны: {strong_str}", W / 2, y, font=R, size=9, color=DIM, align="center")
    y += 7*mm
    _hline(c, ML, y, BW)
    y += 5*mm

    # ── Радарная диаграмма ────────────────────────────────────────────────────
    radar_labels = ["Симметрия", "Пропорции", "Баланс", "Скулы", "Глаза",
                    "Расст.глаз", "Тильт", "Нос", "Губы", "Нос(длина)"]
    radar_fields = ["symmetry_score", "face_proportions_score", "vertical_balance_score",
                    "cheekbones_score", "eyes_score", "eye_distance_score",
                    "canthal_tilt_score", "nose_score", "lips_score", "nose_length_score"]
    radar_scores = [_get_score(metrics, f) for f in radar_fields]

    radar_cx = ML + 58*mm
    radar_cy = _c(y + 42*mm)
    _draw_radar(c, radar_cx, radar_cy, 38*mm, radar_scores, radar_labels)

    # Легенда рядом с радаром
    legend_x = ML + 120*mm
    legend_y = y + 8*mm
    _txt(c, "Профиль метрик", legend_x, legend_y, font=B, size=9, color=WHITE_TXT)
    legend_y += 6*mm
    for field, name, num in METRIC_ORDER_FULL[:10]:
        sc = _get_score(metrics, field)
        bar_w_full = 56*mm
        # Метка — строго НАД баром (baseline at legend_y-1, текст уходит вверх)
        _txt(c, f"{name[:16]}", legend_x, legend_y - 1,
             font=R, size=6, color=WHITE_TXT)
        _txt(c, f"{sc:.1f}", legend_x + bar_w_full + 3, legend_y + 4,
             font=B, size=7, color=_sc(sc))
        # Бар — ниже метки
        _rect(c, legend_x, legend_y + 2, bar_w_full, 4, fill=PANEL)
        _rect(c, legend_x, legend_y + 2, bar_w_full * sc / 10, 4, fill=_sc(sc))
        legend_y += 7.5*mm

    y += 86*mm
    _hline(c, ML, y, BW)
    y += 5*mm

    # Топ-3 + слабые
    half = BW / 2 - 3*mm
    _txt(c, "Топ-3 сильных метрики", ML, y, font=B, size=9, color=WHITE_TXT)
    _txt(c, "Топ-3 зоны потенциала", ML + half + 6*mm, y, font=B, size=9, color=WHITE_TXT)
    y += 6*mm

    for i in range(3):
        sf, ss = strong_3[i]
        wf, ws = weak_3[i]
        _txt(c, f"●  {name_map[sf]}  —  {ss:.2f}", ML + 4, y, font=R, size=8.5, color=C_HIGH)
        _txt(c, f"●  {name_map[wf]}  —  {ws:.2f}", ML + half + 6*mm + 4, y,
             font=R, size=8.5, color=C_LOW)
        y += 5.5*mm

    y += 3*mm
    _hline(c, ML, y, BW)
    y += 5*mm

    # ── ОБЩЕЕ ВПЕЧАТЛЕНИЕ — большой блок ─────────────────────────────────────
    imp_h = 38*mm
    _rect(c, ML, y, BW, imp_h, fill=SURFACE, stroke=LINE, lw=0.5)
    _rect(c, ML, y, BW, 7*mm, fill=PANEL)
    _txt(c, "ОБЩЕЕ ВПЕЧАТЛЕНИЕ", ML + 6, y + 5*mm, font=B, size=10, color=WHITE_TXT)

    # Уровень — справа в шапке блока
    lvl_str = _level_str(metrics.overall_score)
    _txt(c, lvl_str, ML + BW - 4, y + 5*mm, font=B, size=9,
         color=_sc(metrics.overall_score), align="right")

    strong_names = [name_map[f].lower() for f, _ in strong_3]
    weak_names   = [name_map[f].lower() for f, _ in weak_3]

    sym_raw  = metrics.details.get("eye_symmetry", 0)
    ck_raw   = metrics.details.get("cheek_symmetry", 0)
    m_raw    = metrics.details.get("mouth_symmetry", 0)
    sym_val  = round((sym_raw + ck_raw + m_raw) / 30, 3)
    sym_norm = 0.950

    hw_val   = metrics.details.get("face_hw_ratio")
    hw_norm  = 0.896

    impression = (
        f"Лицо с <b>{_level_str(metrics.overall_score).lower()}</b> геометрией. "
        f"Сильные стороны — {', '.join(strong_names)} — "
        f"формируют выразительный, запоминающийся образ. "
        f"Симметрия: {sym_val:.3f} при норме {sym_norm} — "
        f"{'исключительно высокая' if sym_val >= 0.92 else 'хорошая'}. "
    )
    if hw_val:
        impression += (
            f"Пропорции лица (высота/ширина): {hw_val:.3f} при норме {hw_norm} — "
            f"{'удлинённое, мужественное' if hw_val > hw_norm else 'компактное'} лицо. "
        )
    impression += (
        f"Зоны роста — {', '.join(weak_names)} — "
        f"при системной работе существенно усилят общее впечатление."
    )

    _para(c, impression, ML + 6, y + 9*mm, BW - 12, imp_h - 11*mm,
          font=R, size=9, color=WHITE_TXT, align=TA_JUSTIFY, leading=13)
    y += imp_h + 4*mm

    # Таблица вклада всех 20 метрик
    _txt(c, "Все 21 метрику", ML, y, font=B, size=9, color=WHITE_TXT)
    y += 6*mm

    col_w = BW / 2 - 3*mm
    n_metrics = len(METRIC_ORDER_FULL)
    for i in range(0, n_metrics, 2):
        f1, n1, _ = METRIC_ORDER_FULL[i]
        f2, n2, _ = METRIC_ORDER_FULL[i + 1] if i + 1 < n_metrics else (None, "", None)
        s1 = _get_score(metrics, f1)
        s2 = _get_score(metrics, f2) if f2 else None

        _txt(c, n1, ML, y + 3, font=R, size=7.5, color=DIM)
        _txt(c, f"{s1:.2f}", ML + col_w - 4*mm, y + 3, font=B, size=8, color=_sc(s1))

        if f2:
            _txt(c, n2, ML + col_w + 6*mm, y + 3, font=R, size=7.5, color=DIM)
            _txt(c, f"{s2:.2f}", ML + 2 * col_w + 3*mm, y + 3, font=B, size=8, color=_sc(s2))

        _hline(c, ML, y + 4.5*mm, BW, color=LINE, lw=0.3)
        y += 5*mm

    _footer(c, 2, 25)


def _full_metric_page(c, metrics, metric_tuple, m_idx, page_num):
    """Страница метрики (страницы 3–22) с тремя визуализациями."""
    field, name, num = metric_tuple
    score = _get_score(metrics, field)
    sc_col = _sc(score)

    body_text = what_text = influence_text = ""
    meta_key = None
    for sf, mk, body, what, inf in METRICS_20:
        if sf == field:
            body_text = body
            what_text = what
            influence_text = inf
            meta_key = mk
            break

    norm_val = None
    your_val = None
    norm_std  = None
    if meta_key and meta_key in FARKAS_NORMS:
        _, norm_val, detail_key, norm_std = FARKAS_NORMS[meta_key]
        if detail_key:
            your_val = metrics.details.get(detail_key)
        if field == "symmetry_score":
            e  = metrics.details.get("eye_symmetry", 0)
            ck = metrics.details.get("cheek_symmetry", 0)
            m  = metrics.details.get("mouth_symmetry", 0)
            your_val = round((e + ck + m) / 30, 3)

    # ── Фон страницы ──────────────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=BG)

    # ── Шапка ────────────────────────────────────────────────────────────────
    num_str = f"{num:02d} / 20"
    _rect(c, 0, 0, W, MT + 11*mm, fill=SURFACE)
    _txt(c, name, ML, MT + 6*mm, font=B, size=13, color=WHITE_TXT)
    _txt(c, num_str, W - MR, MT + 6*mm, font=R, size=10, color=DIM, align="right")
    _hline(c, 0, MT + 11*mm, W, lw=0.7)

    y = MT + 14*mm

    # ══════════════════════════════════════════════════════════════════════════
    # ВЕРХНЯЯ СЕКЦИЯ  —  3 колонки
    # Левая (38%): спидометр
    # Центр (34%): инфо-панель
    # Правая (28%): процентиль + сравнение
    # ══════════════════════════════════════════════════════════════════════════
    col1_w = BW * 0.37
    col2_w = BW * 0.34
    col3_w = BW * 0.27
    col2_x = ML + col1_w + 3*mm
    col3_x = col2_x + col2_w + 3*mm

    # ── Колонка 1: Спидометр ──────────────────────────────────────────────
    gauge_r  = 25*mm
    gauge_cx = ML + col1_w / 2
    gauge_cy = _c(y + gauge_r + 10*mm)   # canvas y (from bottom)
    _draw_gauge(c, gauge_cx, gauge_cy, gauge_r, score)

    # Уровень под спидометром
    level_y = y + gauge_r * 2 + 13*mm
    _txt(c, _lv(score), ML + col1_w / 2, level_y, font=B, size=10,
         color=sc_col, align="center")

    # Описание уровня
    _para(c, _lv_desc(score), ML + 2, level_y + 5*mm, col1_w - 4, 16,
          font=R, size=7.5, color=DIM, align=TA_CENTER)

    # ── Колонка 2: Инфо-панель ────────────────────────────────────────────
    panel_h = gauge_r * 2 + 16*mm
    _rect(c, col2_x, y, col2_w, panel_h, fill=SURFACE, stroke=LINE, lw=0.5)
    ry = y + 4*mm

    _txt(c, "БАЛЛ", col2_x + 4, ry, font=B, size=7.5, color=DIM)
    ry += 5*mm
    _txt(c, f"{score:.2f} / 10", col2_x + 4, ry, font=B, size=17, color=sc_col)
    _txt(c, _lv(score), col2_x + 4, ry + 6*mm, font=R, size=7.5, color=sc_col)
    ry += 13*mm

    _hline(c, col2_x + 4, ry, col2_w - 8, color=LINE, lw=0.4)
    ry += 4*mm

    _txt(c, "ВАШ ПОКАЗАТЕЛЬ", col2_x + 4, ry, font=B, size=6.5, color=DIM)
    ry += 4.5*mm
    yv_str = str(your_val) if your_val is not None else "—"
    _txt(c, yv_str, col2_x + 4, ry, font=B, size=13, color=WHITE_TXT)
    ry += 7*mm

    _txt(c, "НОРМА (Фаркас)", col2_x + 4, ry, font=B, size=6.5, color=DIM)
    ry += 4.5*mm
    nv_str = str(round(norm_val, 3)) if norm_val is not None else "—"
    _txt(c, nv_str, col2_x + 4, ry, font=B, size=13, color=DIM)
    ry += 7*mm

    # σ-отклонение
    if your_val is not None and norm_val is not None and norm_std:
        sigma_val = abs(your_val - norm_val) / norm_std
        sigma_dir = "↑" if your_val > norm_val else "↓"
        _txt(c, "ОТКЛ. (σ)", col2_x + 4, ry, font=B, size=6.5, color=DIM)
        ry += 4.5*mm
        sigma_col = C_HIGH if sigma_val <= 1.0 else (C_MID if sigma_val <= 2.0 else C_LOW)
        _txt(c, f"{sigma_val:.2f}σ {sigma_dir}", col2_x + 4, ry, font=B, size=12, color=sigma_col)
        ry += 7*mm

    _hline(c, col2_x + 4, ry, col2_w - 8, color=LINE, lw=0.4)
    ry += 4*mm
    _para(c, what_text, col2_x + 4, ry, col2_w - 8, 16,
          font=R, size=7, color=DIM, align=TA_LEFT)

    # ── Колонка 3: Процентиль + сравнение ─────────────────────────────────
    # Процентиль
    _txt(c, "ПОЗИЦИЯ", col3_x, y + 3*mm, font=B, size=7.5, color=DIM)
    _draw_percentile_strip(c, col3_x, y + 7*mm, col3_w, score)

    # Сравнительные бары
    if your_val is not None and norm_val is not None:
        cmp_y = y + 26*mm
        _txt(c, "ВЫ vs НОРМА", col3_x, cmp_y, font=B, size=7.5, color=DIM)
        cmp_y += 4.5*mm
        _draw_comparison_bars(c, col3_x, cmp_y, col3_w, your_val, norm_val)

    # Кривая распределения
    bell_y_top = y + 47*mm
    _txt(c, "РАСПРЕДЕЛЕНИЕ", col3_x, bell_y_top - 1, font=B, size=7.5, color=DIM)
    _draw_bell(c, col3_x, bell_y_top + 15*mm, col3_w, 14*mm, score)

    # ══════════════════════════════════════════════════════════════════════════
    # ТЕКСТ — под верхней секцией
    # ══════════════════════════════════════════════════════════════════════════
    y += panel_h + 4*mm

    # Генерируем динамический текст с реальными значениями
    final_body = _build_dynamic_body(field, body_text, your_val, norm_val, norm_std, score)

    body_frame_h = 42*mm   # ~9 строк при leading=14pt
    _para(c, final_body, ML, y, BW, body_frame_h,
          font=R, size=9.5, color=WHITE_TXT, align=TA_JUSTIFY, leading=14)
    y += body_frame_h + 3*mm

    # ── Блок влияния ──────────────────────────────────────────────────────────
    infl_h = 38*mm
    _rect(c, ML, y, BW, infl_h, fill=INFL_BG, stroke=INFL_BD, lw=1.5)
    _rect(c, ML, y, 4, infl_h, fill=INFL_BD)
    _txt(c, "ВЛИЯНИЕ", ML + 10, y + 5*mm, font=B, size=9, color=INFL_BD)
    # Текстовый фрейм под заголовком «ВЛИЯНИЕ»
    _para(c, influence_text, ML + 10, y + 8*mm, BW - 16, infl_h - 10*mm,
          font=R, size=9.5, color=WHITE_TXT, align=TA_JUSTIFY, leading=14)

    # ── КАК УЛУЧШИТЬ ─────────────────────────────────────────────────────────
    y += infl_h + 4*mm
    advice = METRIC_ADVICE.get(field, "")
    if advice:
        _rect(c, ML, y, BW, 7*mm, fill=PANEL)
        _rect(c, ML, y, 4, 7*mm, fill=C_HIGH)
        _txt(c, "КАК УЛУЧШИТЬ", ML + 10, y + 4.8*mm, font=B, size=8.5, color=C_HIGH)
        y += 9*mm
        _para(c, advice, ML, y, BW, 44*mm,
              font=R, size=9.5, color=DIM, align=TA_JUSTIFY, leading=14)

    _footer(c, page_num, 25)


def generate_full_pdf(metrics: FaceMetrics, name: str = "") -> bytes:
    buf = io.BytesIO()
    c = pdfgen_canvas.Canvas(buf, pagesize=A4)

    # Страница 1: обложка
    _full_cover(c, metrics)
    c.showPage()

    # Страница 2: обзор
    _full_overview(c, metrics)
    c.showPage()

    # Страницы 3–23: 21 метрика
    for i, metric_tuple in enumerate(METRIC_ORDER_FULL):
        _full_metric_page(c, metrics, metric_tuple, i, page_num=3 + i)
        c.showPage()

    # ── Рекомендации и план ────────────────────────────────────────────────────
    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    weak_5 = sorted_asc[:5]
    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}

    # ── Страница 23: Персональные рекомендации по слабым зонам ────────────────
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)
    y23 = MT + 14*mm
    _txt(c, "Персональные рекомендации", ML, y23, font=B, size=14, color=WHITE_TXT)
    _hline(c, ML, y23 + 4*mm, BW, color=LINE)
    y23 += 10*mm
    _para(c,
          "Ниже — конкретные шаги по улучшению твоих трёх наиболее слабых зон. "
          "Начни с первого пункта — он даст максимальный эффект за минимальное время.",
          ML, y23, BW, 16, font=R, size=10, color=DIM, align=TA_JUSTIFY)
    y23 += 18*mm

    for wf, ws in weak_5[:3]:
        wn = name_map[wf]
        advice = METRIC_ADVICE.get(wf, "Работай над этой метрикой системно.")
        _rect(c, ML, y23, BW, 7*mm, fill=PANEL)
        _rect(c, ML, y23, 4, 7*mm, fill=C_LOW)
        _txt(c, f"{wn}  —  {ws:.2f} / 10", ML + 10, y23 + 4.8*mm, font=B, size=9.5, color=WHITE_TXT)
        y23 += 9*mm
        _para(c, advice, ML, y23, BW, 44*mm,
              font=R, size=9.5, color=DIM, align=TA_JUSTIFY, leading=14)
        y23 += 48*mm

    _footer(c, 23, 25)
    c.showPage()

    # ── Страница 24: Глобальные методы улучшения внешности ───────────────────
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)
    y24 = MT + 14*mm
    _txt(c, "40+ методов улучшить внешность", ML, y24, font=B, size=14, color=WHITE_TXT)
    _hline(c, ML, y24 + 4*mm, BW, color=LINE)
    y24 += 10*mm

    improvement_blocks = [
        ("1. Мьюинг (долгосрочно)",
         "Прижимай язык целиком к нёбу — не только кончик. Зубы сомкнуты, губы закрыты, дышишь носом. "
         "Это единственный доказанный метод нехирургического изменения структуры лица у взрослых. "
         "Эффект заметен через 6–24 месяца: подъём скул, улучшение кантального тильта, "
         "более чёткая линия челюсти."),
        ("2. Снижение % жира до 10–13%",
         "Это самый быстрый способ улучшить большинство метрик лица сразу. "
         "Скулы проявляются, подбородок обретает чёткость, нижняя треть становится резкой. "
         "Дефицит калорий 300–500 ккал/день. Протеин 2–2.5 г/кг. Силовые тренировки 3–4 раза в неделю."),
        ("3. Уход за кожей",
         "SPF 30–50 ежедневно — главный антивозрастной инструмент. "
         "Увлажняющий крем утром и вечером поддерживает тургор. "
         "Ретинол 0.025% раз в неделю на ночь — выравнивает текстуру, поры, тон. "
         "Через 3 месяца эффект виден невооружённым глазом."),
        ("4. Брови: форма и заполненность",
         "Правильная форма бровей — один из самых доступных инструментов. "
         "Архитектура: начало — над внутренним углом глаза, конец — у внешнего. "
         "Не выщипывай снизу: это визуально опускает брови. "
         "Карандаш или помада для бровей в тон волосам — заполняет пробелы без искусственного вида."),
        ("5. Причёска и контур лица",
         "Fade / undercut с высокой верхней частью подчёркивает скулы. "
         "Объём на макушке удлиняет лицо — хорошо для круглых форм. "
         "Выбритые виски создают оптический рельеф скуловой кости. "
         "Выбирай причёску, которая визуально компенсирует слабые метрики твоего лица."),
    ]

    for btitle, btext in improvement_blocks:
        if y24 > H - 60*mm:
            break
        _rect(c, ML, y24, BW, 7*mm, fill=PANEL)
        _rect(c, ML, y24, 4, 7*mm, fill=INFL_BD)
        _txt(c, btitle, ML + 10, y24 + 4.8*mm, font=B, size=9.5, color=WHITE_TXT)
        y24 += 9*mm
        _para(c, btext, ML, y24, BW, 36*mm,
              font=R, size=9.5, color=DIM, align=TA_JUSTIFY, leading=14)
        y24 += 40*mm

    _footer(c, 24, 25)
    c.showPage()

    # ── Страница 25: Итог ─────────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=BG)
    _header(c)
    y25 = MT + 14*mm
    _txt(c, "Итог и план действий", ML, y25, font=B, size=14, color=WHITE_TXT)
    _hline(c, ML, y25 + 4*mm, BW, color=LINE)
    y25 += 12*mm

    top = _top_pct(metrics.overall_score)
    _para(c,
          f"Твой итоговый балл {metrics.overall_score:.2f}/10 ставит тебя в топ {top} "
          f"по геометрии лица. Это объективный фундамент — база для работы.",
          ML, y25, BW, 20, font=B, size=11, color=WHITE_TXT, align=TA_CENTER)
    y25 += 22*mm

    all_strong_3 = sorted(all_scores, key=lambda x: x[1], reverse=True)[:3]
    _txt(c, "Твои сильные стороны:", ML, y25, font=B, size=10, color=WHITE_TXT)
    y25 += 6*mm
    for sf, ss in all_strong_3:
        _txt(c, f"  ●  {name_map[sf]}  —  {ss:.2f}/10", ML + 4, y25,
             font=R, size=10, color=C_HIGH)
        y25 += 5.5*mm

    y25 += 5*mm
    _txt(c, "С чего начать прямо сейчас:", ML, y25, font=B, size=10, color=WHITE_TXT)
    y25 += 7*mm

    action_plan = [
        "1.   Мьюинг — начни сегодня. Язык в нёбо, дыши носом.",
        "2.   Снижай % жира: дефицит 300 ккал/день + силовые тренировки.",
        "3.   Введи базовый уход: SPF + увлажнение + ретинол раз в неделю.",
        "4.   Скорректируй причёску под свои слабые метрики.",
        "5.   Оптимизируй сон 7–9 ч и воду 2.5–3 л — убирает отёки лица.",
        "6.   Исправь форму бровей — эффект виден немедленно.",
        "7.   Жвачка Falim 20 мин/день — долгосрочная работа с жевательной мышцей.",
        "8.   Сделай повторный разбор через 6–12 месяцев, чтобы отследить прогресс.",
    ]
    for step in action_plan:
        _para(c, step, ML, y25, BW, 13, font=R, size=10, color=DIM)
        y25 += 14*mm

    y25 += 5*mm
    _hline(c, ML, y25, BW, color=LINE)
    y25 += 10*mm

    _para(c,
          "Красота — это не данность, а процесс. Геометрия задаёт фундамент, "
          "стиль и уход раскрывают его потенциал.",
          ML, y25, BW, 16, font=B, size=11, color=DIM, align=TA_CENTER)
    y25 += 20*mm

    btn_h = 12*mm
    _rect(c, ML, y25, BW, btn_h, fill=INFL_BD)
    _txt(c, f"Telegram: {HANDLE}  —  Qzels Face Bot",
         W / 2, y25 + btn_h / 2 + 1.5*mm, font=B, size=11, color=WHITE_TXT, align="center")

    _footer(c, 25, 25)
    c.showPage()

    c.save()
    return buf.getvalue()
