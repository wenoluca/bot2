"""
PDF-генератор Facedex — белая тема, точная копия дизайна Face Aura.
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

# ── Цвета (белая тема) ────────────────────────────────────────────────────────
WHITE   = colors.HexColor("#FFFFFF")
BLACK   = colors.HexColor("#111111")
GRAY    = colors.HexColor("#555555")
DIM     = colors.HexColor("#888888")
LGRAY   = colors.HexColor("#F5F5F5")
LINE    = colors.HexColor("#DEDEDE")
C_HIGH  = colors.HexColor("#1B5E20")   # зелёный
C_MID   = colors.HexColor("#E65100")   # оранжевый
C_LOW   = colors.HexColor("#B71C1C")   # красный
INFL_BG = colors.HexColor("#EEF3FF")   # фон блока влияния
INFL_BD = colors.HexColor("#1565C0")   # граница
SCORE_BG = colors.HexColor("#FAFAFA")  # фон панели балла

BOT    = "Facedex"
HANDLE = "@facedex_bot"

# ── Вспомогательные ──────────────────────────────────────────────────────────
def _c(y_top): return H - y_top          # from-top → canvas y

def _sc(s):
    if s >= 7.5: return C_HIGH
    if s >= 5.5: return C_MID
    return C_LOW

def _lv(s):
    if s >= 9.0: return "Высоко"
    if s >= 7.5: return "Выше среднего"
    if s >= 5.5: return "Среднее"
    if s >= 4.0: return "Ниже среднего"
    return "Низко"

def _tier_label(t):
    return {"HTN": "High Tier Normie",
            "MTN": "Mid Tier Normie",
            "LTN": "Low Tier Normie"}.get(t, t)

def _top_pct(s):
    if s >= 9.5: return "1%"; 
    if s >= 9.0: return "3%"
    if s >= 8.5: return "7%"
    if s >= 8.0: return "15%"
    if s >= 7.5: return "25%"
    if s >= 7.0: return "35%"
    if s >= 6.5: return "45%"
    return "50–60%"

def _level_str(s):
    if s >= 9.5: return "Исключительно выше среднего"
    if s >= 9.0: return "Значительно выше среднего"
    if s >= 8.5: return "Выше среднего"
    if s >= 8.0: return "Немного выше среднего"
    if s >= 7.0: return "В пределах нормы"
    if s >= 5.5: return "Средний"
    if s >= 4.0: return "Ниже среднего"
    return "Значительно ниже среднего"


def _para(c, text, x, y_top, w, h,
          font=None, size=10, color=None, align=TA_LEFT, leading=None):
    """Параграф с переносом через Frame+Paragraph."""
    font = font or R
    color = color or BLACK
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
    color = color or BLACK
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
    """Шапка страницы: логотип + handle."""
    _txt(c, BOT, W / 2, MT + 5*mm, font=B, size=16, color=BLACK, align="center")
    sub = f"Telegram: {HANDLE}"
    if title_extra: sub = title_extra
    _txt(c, sub, W / 2, MT + 9.5*mm, font=R, size=9, color=DIM, align="center")
    _hline(c, ML, MT + 12*mm, BW, color=LINE, lw=0.7)


# ── Данные метрик ─────────────────────────────────────────────────────────────
FARKAS_NORMS = {
    "symmetry":         ("Симметрия лица",            None,   None),
    "face_proportions": ("Пропорции лица",            0.896,  "face_hw_ratio"),
    "vertical_balance": ("Вертикальный баланс",       0.728,  "vert_balance"),
    "cheekbones":       ("Баланс скул и челюсти",     1.356,  "cheek_jaw_ratio"),
    "eyes":             ("Размер глаз",               0.223,  "eye_to_face"),
    "eye_distance":     ("Расстояние между глазами",  0.271,  "inner_eye_to_face"),
    "canthal_tilt":     ("Наклон глаз",               0.036,  "canthal_norm"),
    "nose":             ("Ширина носа",               0.234,  "nose_to_face"),
    "lips":             ("Ширина рта",                0.403,  "mouth_to_face"),
    "nose_length":      ("Длина носа",                0.421,  "nose_len_ratio"),
    "chin_length":      ("Длина подбородка",          0.283,  "chin_len_ratio"),
    "chin_contour":     ("Контур подбородка",         0.630,  "chin_contour"),
    "nose_to_mouth":    ("Нос к ширине рта",          0.583,  "nose_to_mouth"),
    "biocular":         ("Биокулярная ширина",        0.713,  "biocular_width"),
    "forehead":         ("Ширина лба",                0.919,  "forehead_ratio"),
    "lip_fullness":     ("Полнота губ",               0.347,  "lip_fullness"),
    "lip_ratio":        ("Пропорции губ",             0.639,  "lip_ratio"),
    "jaw_to_mouth":     ("Челюсть к ширине рта",      1.810,  "jaw_to_mouth"),
    "eye_shape":        ("Форма глаз",                0.285,  "eye_shape"),
    "brow_height":      ("Высота бровей",             0.063,  "brow_dist_ratio"),
}

# Порядок 20 метрик: (score_field, meta_key, description_text, what_text, influence_text)
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
     "Норма около 0.063 означает оптимальный зазор, при котором брови выглядят "
     "естественно и гармонично дополняют зону глаз.",
     "Расстояние бровь–глаз / высота лица",
     "Правильная высота бровей обрамляет глаза и акцентирует взгляд. "
     "Слишком высокие брови придают удивлённый вид; слишком низкие — хмурый."),
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
]

BRIEF_GRID = [
    ("symmetry_score",        "Симметрия"),
    ("vertical_balance_score","Вертикальный баланс"),
    ("cheekbones_score",      "Скулы / челюсть"),
    ("eyes_score",            "Размер глаз"),
    ("canthal_tilt_score",    "Наклон глаз"),
    ("nose_score",            "Ширина носа"),
    ("lip_fullness_score",    "Полнота губ"),
    ("chin_contour_score",    "Контур челюсти"),
    ("brow_height_score",     "Высота бровей"),
]

# Советы по слабым метрикам
METRIC_ADVICE = {
    "symmetry_score":
        "Жуй равномерно с обеих сторон. Сон на спине помогает сохранять симметрию. "
        "Проверь прикус у ортодонта — это главная причина лицевой асимметрии. "
        "Избегай постоянного упора щекой в руку.",
    "face_proportions_score":
        "Причёска корректирует форму: высокий объём на макушке визуально удлиняет лицо, "
        "объём по бокам — расширяет. Подбери фасон под желаемые пропорции.",
    "vertical_balance_score":
        "Коррекция трёх третей — задача стилиста. Чёлка балансирует верхнюю треть. "
        "Борода удлиняет или укорачивает нижнюю треть. Работа с мьюингом со временем меняет структуру.",
    "cheekbones_score":
        "Снизь % жира в теле ниже 14% — скулы проявятся. Мьюинг стимулирует рост скул. "
        "Стрижки с выбритыми висками подчёркивают скуловой контур. Жвачка Falim ежедневно.",
    "eyes_score":
        "Убери отёки под глазами: ледяной компресс или нефритовый роллер утром. "
        "Ограничь соль и алкоголь. Сон 8 часов. Ретинол 0.025% снижает пигментацию вокруг глаз.",
    "eye_distance_score":
        "Близкая постановка глаз корректируется причёской с объёмом по бокам и применением "
        "светлых акцентов на внешних уголках. Далёкая — тёмные акценты на внутренних углах.",
    "canthal_tilt_score":
        "Убери отёки нижнего века (сон, вода, меньше соли). Мьюинг поднимает середину лица. "
        "Ледяной роллер по утрам по направлению от носа к вискам.",
    "nose_score":
        "Объём на висках визуально уменьшает нос. Стрижка с широкой верхней частью сужает "
        "восприятие носа. Умеренный контуринг носа работает даже у мужчин.",
    "lips_score":
        "Гидратация делает губы визуально более полными. Скраб для губ раз в неделю. "
        "Увлажняющий бальзам ежедневно. Яркий контур рта подчёркивает правильные пропорции.",
    "nose_length_score":
        "Длинный нос корректируется акцентом на лбу (причёска с объёмом вверх). "
        "Короткий нос — акцент на нижней трети (борода, визуальный вес внизу).",
    "chin_length_score":
        "Борода на подбородке (goatee) визуально удлиняет нижнюю треть. "
        "Мьюинг и правильное положение языка со временем выдвигают подбородок вперёд.",
    "chin_contour_score":
        "Снизь % жира — чёткость подбородочного контура улучшится. Мьюинг помогает. "
        "Стрижка с чёткими краями акцентирует контур.",
    "nose_to_mouth_score":
        "Баланс носа и рта — задача стилиста. Визуально можно скорректировать "
        "контуром губ (подчеркнуть или смягчить) и работой с объёмом причёски.",
    "biocular_score":
        "Биокулярная ширина — костная характеристика. Визуально корректируется "
        "причёской с объёмом у висков и бровями правильной формы.",
    "forehead_score":
        "Широкий лоб балансируется объёмом по бокам и чёлкой. "
        "Узкий лоб — акцент на объёме у висков и широкой верхней части причёски.",
    "lip_fullness_score":
        "Гидратация делает губы полнее. Бальзам + лёгкое растирание кубиком льда. "
        "Нежный скраб раз в неделю. Правильный цвет одежды выделяет зону рта.",
    "lip_ratio_score":
        "Пропорции губ — одна из наименее поддающихся коррекции метрик. "
        "Увлажняй губы ежедневно. При желании — контурирование помадой корректирует визуальный баланс.",
    "jaw_to_mouth_score":
        "Широкий рот визуально сужается тёмными оттенками в уголках. "
        "Узкий рот — светлые центральные акценты. Чёткость челюсти улучшается снижением % жира.",
    "eye_shape_score":
        "Форма глаза — костная характеристика. Горизонтально вытянутые глаза "
        "воспринимаются как более хищные. Убери отёчность верхнего века для более чёткого разреза.",
    "brow_height_score":
        "Правильная форма и высота бровей — один из самых доступных инструментов. "
        "Брови должны начинаться над внутренним углом глаза и заканчиваться у внешнего. "
        "Правильная дуга поднимает взгляд визуально.",
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  КРАТКИЙ РАЗБОР  (2 страницы)                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def generate_brief_pdf(metrics: FaceMetrics, name: str = "") -> bytes:
    buf = io.BytesIO()
    c = pdfgen_canvas.Canvas(buf, pagesize=A4)

    # ── Страница 1 ────────────────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)

    y = MT + 16*mm
    _para(c,
          "Краткий математический разбор геометрии твоего лица.",
          ML, y, BW, 14, font=R, size=11, color=GRAY, align=TA_CENTER)

    # Большой балл
    y += 14
    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 28*mm,
         font=B, size=38, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 28*mm, font=R, size=13, color=DIM, align="left")

    # Тир
    tier_str = f"{metrics.tier}  ·  {_tier_label(metrics.tier)}"
    y += 36*mm
    _txt(c, tier_str, W / 2, y, font=B, size=11, color=BLACK, align="center")
    y += 5*mm
    top = _top_pct(metrics.overall_score)
    _txt(c, f"Ты в топ {top} по геометрии лица!", W / 2, y, font=R, size=10, color=GRAY, align="center")
    y += 5*mm
    _hline(c, ML, y, BW)

    # 3×3 сетка
    y += 5*mm
    card_w = (BW - 2 * 4*mm) / 3
    card_h = 42*mm
    row_gap = 4*mm

    for row in range(3):
        for col in range(3):
            idx = row * 3 + col
            field, label = BRIEF_GRID[idx]
            score = getattr(metrics, field, 5.0)
            sc_col = _sc(score)
            lv = _lv(score)

            cx = ML + col * (card_w + 4*mm)
            cy = y + row * (card_h + row_gap)

            # Карточка фон
            _rect(c, cx, cy, card_w, card_h, fill=LGRAY, stroke=LINE, lw=0.5)

            # Заголовок карточки
            _para(c, label, cx + 3, cy + 5, card_w - 6, 11,
                  font=R, size=9, color=GRAY, align=TA_CENTER)

            # Визуальный бар (тонкая полоска под заголовком)
            bar_w = (card_w - 10) * score / 10
            _rect(c, cx + 5, cy + 17, card_w - 10, 3, fill=LINE)
            _rect(c, cx + 5, cy + 17, bar_w, 3, fill=sc_col)

            # Большой балл
            _txt(c, f"{score:.2f}", cx + card_w / 2, cy + 25*mm,
                 font=B, size=22, color=sc_col, align="center")

            # Уровень
            _txt(c, lv, cx + card_w / 2, cy + 30*mm,
                 font=R, size=8, color=sc_col, align="center")

    _footer(c, 1, 2)
    c.showPage()

    # ── Страница 2 ────────────────────────────────────────────────────────────
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)

    y = MT + 16*mm
    _txt(c, "Краткий разбор — только верхушка.", ML, y, font=B, size=14, color=BLACK)
    y += 7*mm
    _para(c,
          "Этот краткий разбор — лишь небольшая часть полноценного анализа лица.",
          ML, y, BW, 12, font=R, size=11, color=GRAY)
    y += 12*mm
    _para(c,
          "Здесь ты видишь только базовые оценки основных параметров. В полном разборе ты получишь "
          "уже полноценный файл на 25 страниц:",
          ML, y, BW, 22, font=R, size=10, color=BLACK)
    y += 24*mm

    bullets = [
        ("Раскрытие всех оценок: чего не хватает и что нужно улучшать. "
         "Ты сможешь понять, какие особенности делают твоё лицо более гармоничным, "
         "а какие визуально снижают привлекательность и могут мешать восприниматься "
         "более уверенно, статусно и эстетично."),
        ("Подробная оценка общей гармоничности и твоей объективной привлекательности "
         "с подробным описанием."),
        ("Общая статистика из 20 зон лица, по которой ты поймёшь свои сильные и слабые стороны."),
        ("3 страницы конкретных рекомендаций, которые помогут тебе полностью раскрыть свой "
         "потенциал и достичь максимальной красоты."),
    ]
    for bullet in bullets:
        _para(c, f"   •   {bullet}", ML, y, BW, 28, font=R, size=10, color=BLACK, align=TA_JUSTIFY)
        y += 30*mm

    y += 5*mm
    _hline(c, ML, y, BW)
    y += 7*mm

    _para(c,
          "Ты видишь своё лицо каждый день, и твой глаз уже давно замылился.",
          ML, y, BW, 12, font=B, size=11, color=BLACK)
    y += 13*mm
    _para(c,
          "Именно поэтому многие люди годами не понимают, что конкретно портит их внешность и "
          "почему они воспринимаются слабее, менее привлекательно или менее статусно, чем могли бы.\n\n"
          "Полный разбор позволяет посмотреть на своё лицо со стороны — через объективную геометрию, "
          "пропорции и реальные параметры, а далее — приступить к улучшению.",
          ML, y, BW, 50, font=R, size=10, color=BLACK, align=TA_JUSTIFY)
    y += 55*mm

    # Кнопка-блок
    btn_h = 12*mm
    _rect(c, ML, y, BW, btn_h, fill=BLACK)
    _txt(c, "Получить полный разбор  →",
         W / 2, y + btn_h / 2 + 1.5*mm, font=B, size=12, color=WHITE, align="center")

    _footer(c, 2, 2)
    c.showPage()
    c.save()
    return buf.getvalue()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ПОЛНЫЙ РАЗБОР  (25 страниц)                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _get_score(metrics, field):
    return getattr(metrics, field, 5.0)


def _get_raw(metrics, detail_key):
    """Получить сырое значение из details по ключу."""
    if detail_key is None:
        return None
    return metrics.details.get(detail_key)


def _draw_score_bar(c, x, y_top, w, h, score):
    """Горизонтальный бар оценки с отметкой нормы (5.0)."""
    bar_h = 6
    bar_y = y_top + h / 2 - bar_h / 2
    _rect(c, x, bar_y, w, bar_h, fill=LINE)
    fill_w = w * score / 10
    _rect(c, x, bar_y, fill_w, bar_h, fill=_sc(score))
    # Отметка нормы (5.0)
    norm_x = x + w * 0.5
    c.saveState()
    c.setStrokeColor(DIM)
    c.setLineWidth(1)
    c.line(norm_x, _c(bar_y - 2), norm_x, _c(bar_y + bar_h + 2))
    c.restoreState()
    _txt(c, f"{score:.2f}/10", x + w / 2, bar_y - 6, font=B, size=11,
         color=_sc(score), align="center")


def _full_cover(c, metrics):
    """Страница 1 — обложка с фото."""
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)

    y = MT + 16*mm
    _para(c,
          "Полный математический разбор геометрии твоего лица.",
          ML, y, BW, 14, font=R, size=11, color=GRAY, align=TA_CENTER)
    y += 13
    _txt(c, "Открыть бота  →", W / 2, y + 8*mm, font=R, size=9, color=INFL_BD, align="center")
    y += 14*mm

    # Фото
    photo_h = 90*mm
    if metrics.landmark_image:
        try:
            pil = PILImage.open(io.BytesIO(metrics.landmark_image))
            iw, ih = pil.size
            scale = min(BW / iw, photo_h / ih)
            pw, ph = iw * scale, ih * scale
            px = ML + (BW - pw) / 2
            from reportlab.platypus import Image as RLImage
            img = RLImage(io.BytesIO(metrics.landmark_image), width=pw, height=ph)
            img.drawOn(c, px, _c(y + ph))
        except Exception:
            pass

    y += photo_h + 5*mm

    # Балл
    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 14*mm,
         font=B, size=36, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 14*mm, font=R, size=13, color=DIM, align="left")
    y += 20*mm

    top = _top_pct(metrics.overall_score)
    _para(c, f"Ты входишь в топ {top} людей по геометрии лица!",
          ML, y, BW, 14, font=B, size=13, color=BLACK, align=TA_CENTER)
    y += 15*mm

    _txt(c, f"Уровень: {_level_str(metrics.overall_score)}", W / 2, y,
         font=R, size=10, color=GRAY, align="center")
    y += 6*mm

    # Топ-3 сильных
    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    weak_3 = sorted_asc[:3]
    strong_3 = sorted_asc[-3:][::-1]

    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}
    strong_str = ", ".join(name_map[f].lower() for f, _ in strong_3)
    _txt(c, f"Сильные стороны: {strong_str}", W / 2, y,
         font=R, size=9, color=GRAY, align="center")

    _footer(c, 1, 25)


def _full_overview(c, metrics):
    """Страница 2 — сводный обзор."""
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)

    y = MT + 14*mm

    # Балл
    score_col = _sc(metrics.overall_score)
    _txt(c, f"{metrics.overall_score:.2f}", W / 2 - 14*mm, y + 12*mm,
         font=B, size=34, color=score_col, align="right")
    _txt(c, "из 10", W / 2 - 11*mm, y + 12*mm, font=R, size=12, color=DIM, align="left")
    y += 18*mm

    top = _top_pct(metrics.overall_score)
    _para(c, f"Ты входишь в топ {top} людей по геометрии лица!",
          ML, y, BW, 12, font=B, size=11, color=BLACK, align=TA_CENTER)
    y += 13*mm

    _txt(c, f"Уровень: {_level_str(metrics.overall_score)}", W / 2, y,
         font=R, size=10, color=GRAY, align="center")
    y += 6*mm

    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    weak_3 = sorted_asc[:3]
    strong_3 = sorted_asc[-3:][::-1]
    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}
    strong_str = ", ".join(name_map[f].lower() for f, _ in strong_3)
    _txt(c, f"Сильные стороны: {strong_str}", W / 2, y, font=R, size=9, color=GRAY, align="center")
    y += 7*mm
    _hline(c, ML, y, BW)
    y += 5*mm

    # ОБЩЕЕ ВПЕЧАТЛЕНИЕ
    _txt(c, "ОБЩЕЕ ВПЕЧАТЛЕНИЕ", ML, y, font=B, size=10, color=BLACK)
    y += 6*mm

    # Генерируем текст впечатления
    strong_names = [name_map[f].lower() for f, _ in strong_3]
    weak_names = [name_map[f].lower() for f, _ in weak_3]
    impression = (
        f"Лицо с {_level_str(metrics.overall_score).lower()} геометрией. "
        f"Ключевые сильные стороны — {', '.join(strong_names)} — "
        f"формируют выразительный, запоминающийся образ. "
        f"Зоны потенциала — {', '.join(weak_names)} — при грамотной работе могут "
        f"существенно усилить общее впечатление."
    )
    _para(c, impression, ML, y, BW, 28, font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)
    y += 30*mm

    # Профиль метрик (мини-бары)
    _txt(c, "Профиль метрик", ML, y, font=B, size=10, color=BLACK)
    y += 7*mm

    bar_row_h = 6*mm
    bar_bar_w = 80*mm
    bar_lbl_w = 65*mm
    bar_score_w = 15*mm

    for field, name, num in METRIC_ORDER_FULL:
        score = _get_score(metrics, field)
        sc = _sc(score)
        # label
        _txt(c, name, ML, y + 3.5, font=R, size=7.5, color=BLACK)
        # bar background
        bx = ML + bar_lbl_w
        _rect(c, bx, y + 1, bar_bar_w, 3.5, fill=LINE)
        _rect(c, bx, y + 1, bar_bar_w * score / 10, 3.5, fill=sc)
        # score
        _txt(c, f"{score:.2f}", bx + bar_bar_w + 3, y + 3.5, font=B, size=7.5, color=sc)
        y += bar_row_h
        if y > H - 60*mm:
            break  # safety

    y += 5*mm
    _hline(c, ML, y, BW)
    y += 5*mm

    # Топ-3 сильных / зоны потенциала
    half = BW / 2 - 3*mm
    _txt(c, "Топ-3 сильных метрики", ML, y, font=B, size=9, color=BLACK)
    _txt(c, "Топ-3 зоны потенциала", ML + half + 6*mm, y, font=B, size=9, color=BLACK)
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

    # Вклад каждой метрики (2-колоночная таблица)
    _txt(c, "Вклад каждой метрики", ML, y, font=B, size=10, color=BLACK)
    y += 7*mm

    col_w = BW / 2 - 3*mm
    for i in range(0, 20, 2):
        f1, n1, _ = METRIC_ORDER_FULL[i]
        f2, n2, _ = METRIC_ORDER_FULL[i + 1] if i + 1 < 20 else (None, "", None)
        s1 = _get_score(metrics, f1)
        s2 = _get_score(metrics, f2) if f2 else None

        # Left entry
        _txt(c, n1, ML, y + 3.5, font=R, size=8.5, color=BLACK)
        _txt(c, f"{s1:.2f}", ML + col_w - 5*mm, y + 3.5, font=B, size=8.5, color=_sc(s1))

        # Right entry
        if f2:
            _txt(c, n2, ML + col_w + 6*mm, y + 3.5, font=R, size=8.5, color=BLACK)
            _txt(c, f"{s2:.2f}", ML + 2 * col_w + 3*mm, y + 3.5,
                 font=B, size=8.5, color=_sc(s2))

        _hline(c, ML, y + 5*mm, BW, color=colors.HexColor("#F0F0F0"), lw=0.3)
        y += 5.5*mm

    _footer(c, 2, 25)


def _full_metric_page(c, metrics, metric_tuple, m_idx, page_num):
    """Страница метрики (страницы 3–22)."""
    field, name, num = metric_tuple
    score = _get_score(metrics, field)
    sc_col = _sc(score)

    # Находим описание
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
    if meta_key and meta_key in FARKAS_NORMS:
        _, norm_val, detail_key = FARKAS_NORMS[meta_key]
        if detail_key:
            your_val = metrics.details.get(detail_key)
            if your_val is None:
                # symmetry special case
                if field == "symmetry_score":
                    e = metrics.details.get("eye_symmetry", 0)
                    ck = metrics.details.get("cheek_symmetry", 0)
                    m = metrics.details.get("mouth_symmetry", 0)
                    your_val = round((e + ck + m) / 30, 3)

    _rect(c, 0, 0, W, H, fill=WHITE)

    # Заголовок метрики
    num_str = f"{num:02d} / 20"
    _txt(c, name, ML, MT + 6*mm, font=B, size=13, color=BLACK)
    _txt(c, num_str, W - MR, MT + 6*mm, font=R, size=10, color=DIM, align="right")
    _hline(c, ML, MT + 9*mm, BW, lw=0.7)

    y = MT + 13*mm

    # Левая колонка: визуализация балла
    left_w = 90*mm
    right_w = BW - left_w - 6*mm
    right_x = ML + left_w + 6*mm

    # Бар оценки
    bar_w = left_w - 10*mm
    bar_x = ML + 5*mm
    bar_y_top = y + 8*mm
    _draw_score_bar(c, bar_x, bar_y_top, bar_w, 14*mm, score)

    # Уровень
    _txt(c, _lv(score), bar_x + bar_w / 2, bar_y_top + 18*mm,
         font=R, size=9, color=sc_col, align="center")

    # Правая колонка: информационный блок
    _rect(c, right_x, y, right_w, 38*mm, fill=SCORE_BG, stroke=LINE, lw=0.5)
    ry = y + 4*mm
    _txt(c, "Балл метрики", right_x + 4, ry, font=R, size=8, color=DIM)
    ry += 5*mm
    _txt(c, f"{score:.2f} / 10", right_x + 4, ry, font=B, size=16, color=sc_col)
    ry += 7*mm
    _txt(c, "ВАШ ПОКАЗАТЕЛЬ", right_x + 4, ry, font=B, size=7, color=DIM)
    ry += 4*mm
    if your_val is not None:
        _txt(c, str(your_val), right_x + 4, ry, font=R, size=10, color=BLACK)
    _para(c, what_text, right_x + 4, ry + 3, right_w - 8, 12,
          font=R, size=7.5, color=DIM)
    ry += 11*mm
    _txt(c, "НОРМА", right_x + 4, ry, font=B, size=7, color=DIM)
    ry += 4*mm
    if norm_val is not None:
        _txt(c, str(round(norm_val, 3)), right_x + 4, ry, font=R, size=10, color=BLACK)
    else:
        _txt(c, "—", right_x + 4, ry, font=R, size=10, color=BLACK)

    # Тело страницы
    y += 43*mm
    _para(c, body_text, ML, y, BW, 45,
          font=R, size=10, color=BLACK, align=TA_JUSTIFY, leading=15)
    y += 47*mm

    # Блок влияния
    infl_h = 22*mm
    _rect(c, ML, y, BW, infl_h, fill=INFL_BG, stroke=INFL_BD, lw=0.8)
    _txt(c, "ВЛИЯНИЕ", ML + 5, y + 5*mm, font=B, size=8, color=INFL_BD)
    _para(c, influence_text, ML + 5, y + 6*mm, BW - 10, infl_h - 7*mm,
          font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)

    _footer(c, page_num, 25)


def _full_rec_page(c, title, content_blocks, page_num):
    """Страница рекомендаций."""
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)

    y = MT + 14*mm
    _txt(c, title, ML, y, font=B, size=14, color=BLACK)
    _hline(c, ML, y + 4*mm, BW)
    y += 10*mm

    for block_title, block_text in content_blocks:
        # Заголовок блока
        _rect(c, ML, y, BW, 7*mm, fill=LGRAY)
        _txt(c, block_title, ML + 4, y + 4.5*mm, font=B, size=9.5, color=BLACK)
        y += 9*mm
        _para(c, block_text, ML, y, BW, 30,
              font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)
        y += 32*mm
        if y > H - 30*mm:
            break


def generate_full_pdf(metrics: FaceMetrics, name: str = "") -> bytes:
    buf = io.BytesIO()
    c = pdfgen_canvas.Canvas(buf, pagesize=A4)

    # Страница 1: обложка
    _full_cover(c, metrics)
    c.showPage()

    # Страница 2: обзор
    _full_overview(c, metrics)
    c.showPage()

    # Страницы 3–22: 20 метрик
    for i, metric_tuple in enumerate(METRIC_ORDER_FULL):
        _full_metric_page(c, metrics, metric_tuple, i, page_num=3 + i)
        c.showPage()

    # Страницы 23–25: рекомендации
    all_scores = [(f, getattr(metrics, f, 5.0)) for f, _, __ in METRIC_ORDER_FULL]
    sorted_asc = sorted(all_scores, key=lambda x: x[1])
    weak_5 = sorted_asc[:5]
    name_map = {f: n for f, n, _ in METRIC_ORDER_FULL}

    # Страница 23: Слабые зоны
    blocks_23 = []
    for wf, ws in weak_5[:3]:
        wn = name_map[wf]
        advice = METRIC_ADVICE.get(wf, "Работай над этой метрикой системно.")
        blocks_23.append((f"{wn}  —  {ws:.2f} / 10", advice))

    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)
    y23 = MT + 14*mm
    _txt(c, "Рекомендации по слабым зонам", ML, y23, font=B, size=14, color=BLACK)
    _hline(c, ML, y23 + 4*mm, BW)
    y23 += 10*mm
    _para(c,
          "Ниже представлены конкретные шаги по улучшению трёх наиболее слабых метрик твоего лица. "
          "Начни с первого пункта — он даст максимальный эффект.",
          ML, y23, BW, 16, font=R, size=10, color=GRAY, align=TA_JUSTIFY)
    y23 += 18*mm

    for block_title, block_text in blocks_23:
        _rect(c, ML, y23, BW, 7*mm, fill=LGRAY)
        _txt(c, block_title, ML + 4, y23 + 4.5*mm, font=B, size=9.5, color=BLACK)
        y23 += 9*mm
        _para(c, block_text, ML, y23, BW, 28,
              font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)
        y23 += 32*mm

    _footer(c, 23, 25)
    c.showPage()

    # Страница 24: Ещё 2 зоны + уход
    blocks_24 = []
    for wf, ws in weak_5[3:5]:
        wn = name_map[wf]
        advice = METRIC_ADVICE.get(wf, "Работай над этой метрикой системно.")
        blocks_24.append((f"{wn}  —  {ws:.2f} / 10", advice))

    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)
    y24 = MT + 14*mm
    _txt(c, "Уход и стиль", ML, y24, font=B, size=14, color=BLACK)
    _hline(c, ML, y24 + 4*mm, BW)
    y24 += 10*mm

    for block_title, block_text in blocks_24:
        _rect(c, ML, y24, BW, 7*mm, fill=LGRAY)
        _txt(c, block_title, ML + 4, y24 + 4.5*mm, font=B, size=9.5, color=BLACK)
        y24 += 9*mm
        _para(c, block_text, ML, y24, BW, 28,
              font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)
        y24 += 32*mm

    care_blocks = [
        ("Базовый уход за кожей",
         "SPF 30–50 каждый день без исключений — главный антивозрастной инструмент. "
         "Увлажняющий крем утром и вечером. Ретинол 0.025% на ночь раз в неделю — "
         "выравнивает текстуру и поры. Через 3 месяца результат будет заметен."),
        ("Сон и образ жизни",
         "7–9 часов сна снижают отёчность и улучшают кожу. "
         "Вода 2.5–3 л/день убирает задержку жидкости в лице. "
         "Ограничь сахар и переработанные продукты — кожа реагирует в течение 2–3 дней."),
    ]
    for block_title, block_text in care_blocks:
        if y24 > H - 50*mm:
            break
        _rect(c, ML, y24, BW, 7*mm, fill=LGRAY)
        _txt(c, block_title, ML + 4, y24 + 4.5*mm, font=B, size=9.5, color=BLACK)
        y24 += 9*mm
        _para(c, block_text, ML, y24, BW, 28,
              font=R, size=9.5, color=BLACK, align=TA_JUSTIFY)
        y24 += 32*mm

    _footer(c, 24, 25)
    c.showPage()

    # Страница 25: Итог
    _rect(c, 0, 0, W, H, fill=WHITE)
    _header(c)
    y25 = MT + 14*mm
    _txt(c, "Итог и план действий", ML, y25, font=B, size=14, color=BLACK)
    _hline(c, ML, y25 + 4*mm, BW)
    y25 += 12*mm

    top = _top_pct(metrics.overall_score)
    _para(c,
          f"Твой итоговый балл {metrics.overall_score:.2f}/10 ставит тебя в топ {top} "
          f"по геометрии лица. Это объективный результат — хорошая база для работы.",
          ML, y25, BW, 20, font=B, size=11, color=BLACK, align=TA_CENTER)
    y25 += 22*mm

    all_strong_3 = sorted(all_scores, key=lambda x: x[1], reverse=True)[:3]
    _txt(c, "Твои сильные стороны:", ML, y25, font=B, size=10, color=BLACK)
    y25 += 6*mm
    for sf, ss in all_strong_3:
        _txt(c, f"  ●  {name_map[sf]}  —  {ss:.2f}/10", ML + 4, y25,
             font=R, size=10, color=C_HIGH)
        y25 += 5.5*mm

    y25 += 5*mm
    _txt(c, "С чего начать:", ML, y25, font=B, size=10, color=BLACK)
    y25 += 7*mm

    action_plan = [
        "1.   Пройди по рекомендациям из страниц 23–24 — начни с первого пункта.",
        "2.   Введи базовый уход за кожей (SPF + увлажнение + ретинол).",
        "3.   Начни мьюинг — это долгосрочное изменение структуры лица.",
        "4.   Оптимизируй сон и питание — быстрый вклад в качество кожи.",
        "5.   Сделай повторный разбор через 6–12 месяцев, чтобы отследить прогресс.",
    ]
    for step in action_plan:
        _para(c, step, ML, y25, BW, 14, font=R, size=10, color=BLACK)
        y25 += 15*mm

    y25 += 5*mm
    _hline(c, ML, y25, BW)
    y25 += 10*mm

    _para(c,
          "Красота — это не данность, а процесс. Геометрия задаёт фундамент, "
          "стиль и уход раскрывают его потенциал.",
          ML, y25, BW, 16, font=B, size=11, color=GRAY, align=TA_CENTER)
    y25 += 20*mm

    # Финальный блок-кнопка
    btn_h = 12*mm
    _rect(c, ML, y25, BW, btn_h, fill=BLACK)
    _txt(c, f"Telegram: {HANDLE}  —  Facedex",
         W / 2, y25 + btn_h / 2 + 1.5*mm, font=B, size=11, color=WHITE, align="center")

    _footer(c, 25, 25)
    c.showPage()

    c.save()
    return buf.getvalue()
