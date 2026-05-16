"""
PDF-генератор Facedex — краткий и полный разбор.
DejaVuSans — кириллица. Фиксированный макет без перекрытий.
"""
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from face_analyzer import FaceMetrics

# ── Шрифты ───────────────────────────────────────────────────────────────────
_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DV",  _FONT_PATH))
pdfmetrics.registerFont(TTFont("DVB", _FONT_PATH))
REGULAR, BOLD = "DV", "DVB"

# ── Цвета ────────────────────────────────────────────────────────────────────
BG     = colors.HexColor("#0B0B0F")
PANEL  = colors.HexColor("#17171E")
PANEL2 = colors.HexColor("#111116")
GOLD   = colors.HexColor("#C9A84C")
GOLDB  = colors.HexColor("#E8C96A")
TEXT   = colors.HexColor("#EEEEF2")
DIM    = colors.HexColor("#6A6A80")
GREEN  = colors.HexColor("#4CAF50")
ORANGE = colors.HexColor("#FF9800")
RED    = colors.HexColor("#F44336")
BORDER = colors.HexColor("#28283A")
ACCENT = colors.HexColor("#1E1E2C")
HEADER = colors.HexColor("#0D0D14")

W, H = A4
BODY  = W - 36*mm  # 174 mm usable


def _sc(s): return GREEN if s >= 7.5 else (ORANGE if s >= 5.5 else RED)
def _sh(s): return "#4CAF50" if s >= 7.5 else ("#FF9800" if s >= 5.5 else "#F44336")
def _bar(s, n=22): filled = round(s / 10 * n); return "█" * filled + "░" * (n - filled)

def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG); canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(GOLD); canvas.rect(0, H - 3, W, 3, fill=1, stroke=0)
    canvas.restoreState()

def _s(name, **kw):
    d = dict(fontName=REGULAR, textColor=TEXT, fontSize=10, leading=14, spaceAfter=0)
    d.update(kw); return ParagraphStyle(name, **d)

def _make_doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm)

def _tier_label(t):
    return {"HTN":"High Tier Normie","MTN":"Mid Tier Normie","LTN":"Low Tier Normie"}.get(t, t)

def _photo(data, max_w=88*mm, max_h=88*mm):
    try:
        pil = PILImage.open(io.BytesIO(data))
        iw, ih = pil.size
        r = min(max_w / iw, max_h / ih)
        img = RLImage(io.BytesIO(data), width=iw*r, height=ih*r)
        img.hAlign = "CENTER"
        return img
    except Exception:
        return None

# ── Секция ───────────────────────────────────────────────────────────────────
def _section(text):
    return [
        Spacer(1, 4*mm),
        Paragraph(text, _s("sh", fontName=BOLD, fontSize=11, textColor=GOLDB, spaceAfter=1*mm)),
        HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3*mm),
    ]

# ── Бейдж с итоговым баллом ──────────────────────────────────────────────────
def _score_badge(score, grade, tier):
    col = _sc(score)
    badge = Table([[
        Paragraph(f"{score:.1f}<font size='18'>/10</font>",
                  _s("num", fontName=BOLD, fontSize=36, textColor=col, leading=42,
                     alignment=TA_CENTER)),
        Table([[
            Paragraph(grade,
                      _s("gr", fontName=BOLD, fontSize=13, textColor=TEXT, leading=18)),
            Paragraph(f"{tier}  —  {_tier_label(tier)}",
                      _s("tr", fontSize=10, textColor=DIM, leading=14)),
        ]], colWidths=[None])
    ]], colWidths=[52*mm, None])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), ACCENT),
        ("BOX",           (0,0),(-1,-1), 1.5, GOLD),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("LINEAFTER",     (0,0),(0,-1), 1.5, GOLD),
    ]))
    return badge

# ── Таблица параметров — 3 чётких колонки без перекрытий ────────────────────
# Колонки: [Параметр 64mm] [Балл 18mm] [Бар + строка "X.X → идеал: Y" 92mm]
_COL = [64*mm, 18*mm, 92*mm]

def _metric_row(name, score, measured_str, ideal_str):
    bar = _bar(score)
    detail = f"{measured_str}  →  идеал: {ideal_str}"
    return [
        Paragraph(name, _s("rn", fontSize=9, textColor=TEXT, leading=13)),
        Paragraph(f'<font color="{_sh(score)}">{score:.1f}</font>',
                  _s("rs", fontName=BOLD, fontSize=13, alignment=TA_CENTER, leading=16)),
        Table([[
            Paragraph(f'<font name="Courier" size="8" color="#C9A84C">{bar}</font>',
                      _s("bar", fontSize=8, leading=11)),
            Paragraph(detail, _s("det", fontSize=8, textColor=DIM, leading=11)),
        ]], colWidths=[None]),
    ]

def _params_table(rows):
    """rows = list of (name, score, measured_str, ideal_str)"""
    hdr = [
        Paragraph("Параметр",    _s("h0", fontName=BOLD, fontSize=9, textColor=GOLDB)),
        Paragraph("Балл",        _s("h1", fontName=BOLD, fontSize=9, textColor=GOLDB, alignment=TA_CENTER)),
        Paragraph("Бар  /  Твоё значение  →  Идеал",
                  _s("h2", fontName=BOLD, fontSize=9, textColor=GOLDB)),
    ]
    tdata = [hdr] + [_metric_row(*r) for r in rows]
    tbl = Table(tdata, colWidths=_COL, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), HEADER),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [PANEL, PANEL2]),
        ("BOX",           (0,0),(-1,-1), 0.6, GOLD),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
    ]))
    return tbl

# ── Таблица измерений ─────────────────────────────────────────────────────────
def _meas_table(rows):
    hdr = [Paragraph(h, _s(f"mh{i}", fontName=BOLD, fontSize=9, textColor=GOLDB,
                            alignment=TA_LEFT if i%2==0 else TA_CENTER))
           for i, h in enumerate(["Параметр","Значение","Параметр","Значение"])]
    tdata = [hdr]
    for r in rows:
        tdata.append([
            Paragraph(str(r[0]), _s("ml", fontSize=9, textColor=TEXT, leading=12)),
            Paragraph(str(r[1]), _s("mv", fontName=BOLD, fontSize=9, textColor=GOLDB, alignment=TA_CENTER)),
            Paragraph(str(r[2]), _s("mr", fontSize=9, textColor=TEXT, leading=12)),
            Paragraph(str(r[3]), _s("mw", fontName=BOLD, fontSize=9, textColor=GOLDB, alignment=TA_CENTER)),
        ])
    tbl = Table(tdata, colWidths=[60*mm, 24*mm, 60*mm, 22*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), HEADER),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [PANEL, PANEL2]),
        ("BOX",           (0,0),(-1,-1), 0.6, GOLD),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
    ]))
    return tbl

# ── Блок совета ──────────────────────────────────────────────────────────────
def _advice_card(emoji, title, text):
    return KeepTogether(Table([[
        Paragraph(emoji, _s("ae", fontName=BOLD, fontSize=16, alignment=TA_CENTER,
                            textColor=GOLDB, leading=20)),
        Table([[
            Paragraph(title, _s("at", fontName=BOLD, fontSize=10, textColor=GOLDB, leading=14)),
            Paragraph(text,  _s("ab", fontSize=9, textColor=TEXT, leading=14)),
        ]], colWidths=[None]),
    ]], colWidths=[14*mm, None],
    style=TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), PANEL),
        ("BOX",          (0,0),(-1,-1), 0.5, BORDER),
        ("LINEAFTER",    (0,0),(0,-1), 1.5, GOLD),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ])))

# ── Советы ───────────────────────────────────────────────────────────────────
def _advice(m: FaceMetrics):
    tips = []

    # Золотое сечение
    if m.golden_ratio_score >= 8:
        tips.append(("📐", "Золотое сечение — отлично",
                     "Пропорции близки к φ=1.618. Следи за весом: +3 кг изменяют форму лица. Ограничь соль и алкоголь — они дают отёчность."))
    else:
        tips.append(("📐", "Золотое сечение — есть запас",
                     "Мьюинг (язык прижат к нёбу 24/7) постепенно корректирует форму лица. Жуй жёсткую жвачку Falim 20 мин в день — нагружает жевательные мышцы."))

    # Симметрия
    if m.symmetry_score >= 8.5:
        tips.append(("🪞", "Симметрия — высокая",
                     "Не спи постоянно на одной стороне. Следи за прикусом — неравномерный жевательный тонус смещает симметрию."))
    else:
        tips.append(("🪞", "Симметрия — есть асимметрия",
                     "Жуй поровну с обеих сторон. Сон на спине сохраняет симметрию. Проверь прикус у ортодонта — это главная причина асимметрии лица."))

    # Кантальный тильт
    if m.canthal_tilt_degrees >= 5:
        tips.append(("👁", "Кантальный тильт — позитивный",
                     f"Угол {m.canthal_tilt_degrees:+.1f}° — «охотничьи глаза». Мьюинг и низкий % жира поддерживают этот эффект. Избегай пуфа под глазами: меньше соли, больше сна."))
    elif m.canthal_tilt_degrees >= 0:
        tips.append(("👁", "Кантальный тильт — нейтральный",
                     f"Угол {m.canthal_tilt_degrees:+.1f}°. Убирай отёки под глазами: ледяной кубик или нефритовый роллер утром. Мьюинг со временем поднимает средину лица."))
    else:
        tips.append(("👁", "Кантальный тильт — отрицательный",
                     f"Угол {m.canthal_tilt_degrees:+.1f}° — визуально устаёт лицо. Приоритет: убрать отёки (сон 8ч, нет соли, нет алкоголя). Роллер из нефрита по утрам. Мьюинг обязателен."))

    # Челюсть
    if m.jaw_score >= 8:
        tips.append(("💪", "Линия челюсти — чёткая",
                     "Стрижка с выбритыми висками (андеркат, тейпер) подчёркивает контур. Держи % жира в теле ниже 15% — это делает скулы и челюсть рельефными."))
    else:
        tips.append(("💪", "Линия челюсти — нужна работа",
                     "Три ключевых инструмента: 1) мьюинг, 2) жёсткая жвачка Falim ежедневно, 3) снижение % жира. Стрижка «длинные виски» скрывает нечёткий контур."))

    # Брови
    if m.eyebrows_score < 7:
        tips.append(("↑", "Брови — густота и форма",
                     "Наноси сыворотку для бровей с биотином или пептидами (Brow Serum) каждый вечер. Дугообразная форма бровей до ширины крыльев носа — классический идеал. Мужские брови не должны быть слишком тонкими."))

    # Нос
    if m.nose_score < 7:
        tips.append(("👃", "Нос — визуальная коррекция",
                     "Объём на висках визуально уменьшает нос. Стрижка с более широкой верхней частью сужает восприятие носа. Лёгкий контуринг носа (тёмная тень по бокам) — работает даже у мужчин в HD-формате."))

    # Трети лица / причёска
    if m.facial_thirds_score < 7.5:
        tips.append(("✂️", "Причёска и трети лица",
                     "Трети лица корректируются причёской: высокий лоб — чёлка или зачёс вперёд; низкий лоб — зачёс назад, объём на макушке. Стрижка «до ушей» с открытой шеей подчёркивает скулы и удлиняет лицо."))
    else:
        tips.append(("✂️", "Причёска — подчеркни сильные стороны",
                     "Стрижка до ушей открывает скулы и подчёркивает челюсть. Андеркат или тейпер по бокам добавляет «структуру» лицу. Объём на макушке визуально удлиняет лицо."))

    # Кожа — всегда
    tips.append(("🧴", "Уход за кожей — базовый стек",
                 "SPF 30–50 каждый день (без исключений) — главный антивозрастной инструмент. Увлажняющий крем утром и вечером. Ретинол 0.025% на ночь раз в неделю для начала — выравнивает текстуру и поры."))

    # Сон / образ жизни — всегда
    tips.append(("🌙", "Сон и образ жизни",
                 "7–9 часов сна снижают отёчность и улучшают кожу. Вода 2.5–3 л/день убирает задержку жидкости в лице. Ограничь сахар и переработанные продукты — кожа реагирует в течение 2–3 дней."))

    return tips


# ════════════════════════════════════════════════════════════════════════════
#  КРАТКИЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_brief_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st = []

    # Шапка
    st.append(Paragraph("FACEDEX", _s("t", fontName=BOLD, fontSize=28, textColor=GOLD,
                                      alignment=TA_CENTER, spaceAfter=1*mm)))
    st.append(Paragraph(f"Краткий разбор  •  @{username}",
                        _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER, spaceAfter=3*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=4*mm))

    # Фото
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image)
        if ph:
            st.append(ph); st.append(Spacer(1, 4*mm))

    # Бейдж
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 5*mm))

    # Параметры
    st += _section("ОЦЕНКА ПО КЛЮЧЕВЫМ ПАРАМЕТРАМ")
    params = [
        ("👁  Глаза",     metrics.eyes_score,        "–",     "ширина гл./лицо ≈ 0.20"),
        ("👃  Нос",       metrics.nose_score,         "–",     "ширина носа/лицо ≈ 0.20"),
        ("👄  Губы",      metrics.lips_score,         "–",     "рот/МЗР ≈ 1.00"),
        ("🦴  Скулы",     metrics.cheekbones_score,   "–",     "скулы/чел ≈ 1.30"),
        ("💪  Челюсть",   metrics.jaw_score,          "–",     "чел/скулы ≈ 0.75"),
        ("↑   Брови",     metrics.eyebrows_score,     "–",     "позиция бровей"),
        ("🪞  Симметрия", metrics.symmetry_score,     "–",     "идеал 10/10"),
        ("⚖   Баланс",    metrics.balance_score,      "–",     "среднее 3х пропорций"),
    ]
    st.append(_params_table(params))
    st.append(Spacer(1, 5*mm))

    # Подсказка
    _hint_tbl = Table([[Paragraph(
        "📊  Хочешь полный анализ?\n"
        "Полный разбор: 11 метрик, нормы Лесли Фаркаса, "
        "персональные советы по внешности и причёске.",
        _s("hint", fontSize=9, textColor=DIM, leading=14)
    )]], colWidths=[BODY])
    _hint_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), PANEL),
        ("BOX",          (0,0),(-1,-1), 0.5, BORDER),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    st.append(KeepTogether(_hint_tbl))
    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph("Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
                        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER)))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  ПОЛНЫЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_full_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    d = metrics.details or {}
    fw = metrics.face_width or 1
    ipd = metrics.interpupillary_distance or 1
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st = []

    # Шапка
    st.append(Paragraph("FACEDEX", _s("t", fontName=BOLD, fontSize=28, textColor=GOLD,
                                      alignment=TA_CENTER, spaceAfter=1*mm)))
    st.append(Paragraph(f"Полный разбор  •  @{username}",
                        _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER, spaceAfter=3*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=4*mm))

    # Фото
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image)
        if ph:
            st.append(ph); st.append(Spacer(1, 4*mm))

    # Бейдж
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 5*mm))

    # Параметры с реальными значениями и идеалами
    hw  = round(d.get("face_hw_ratio", 0), 3)
    ey  = round(d.get("eye_symmetry", 0), 1)
    ck  = round(d.get("cheek_symmetry", 0), 1)
    mo  = round(d.get("mouth_symmetry", 0), 1)
    up  = round(d.get("upper_third_pct", 0), 1)
    mi  = round(d.get("middle_third_pct", 0), 1)
    lo  = round(d.get("lower_third_pct", 0), 1)
    jcr = round(d.get("jaw_to_cheek_ratio", 0), 3)
    ipr = round(d.get("ipd_to_face_ratio", 0), 3)
    cjr = round(d.get("cheek_jaw_ratio", 0), 3)
    le  = round(metrics.left_eye_width  / fw, 3) if fw else 0
    nr  = round(metrics.nose_width      / fw, 3) if fw else 0
    mr  = round(metrics.mouth_width     / ipd, 3) if ipd else 0
    br  = round(d.get("brow_dist_ratio", 0.065), 3)

    st += _section("ОЦЕНКА ПО 11 ПАРАМЕТРАМ")
    params = [
        ("📐  Золотое сечение (φ)", metrics.golden_ratio_score,
         f"H/W={hw}",                    "φ = 1.618"),
        ("🪞  Симметрия",            metrics.symmetry_score,
         f"Гл:{ey} Ск:{ck} Рот:{mo}",   "каждый → 10.0"),
        ("📏  Трети лица",           metrics.facial_thirds_score,
         f"В:{up}% С:{mi}% Н:{lo}%",    "33% / 33% / 33%"),
        ("👁  Кантальный тильт",     metrics.canthal_tilt_score,
         f"угол {metrics.canthal_tilt_degrees:+.1f}°",  "+5° … +10°"),
        ("💪  Челюсть",              metrics.jaw_score,
         f"чел/скулы {jcr}",            "≈ 0.75"),
        ("👁  Глаза",                metrics.eyes_score,
         f"гл/лицо {le}",              "≈ 0.200"),
        ("👃  Нос",                  metrics.nose_score,
         f"нос/лицо {nr}",             "≈ 0.200"),
        ("👄  Губы",                 metrics.lips_score,
         f"рот/МЗР {mr}",             "≈ 1.000"),
        ("🦴  Скулы",                metrics.cheekbones_score,
         f"скулы/чел {cjr}",           "≈ 1.300"),
        ("↑   Брови",               metrics.eyebrows_score,
         f"отступ/лицо {br}",          "≈ 0.065"),
        ("⚖   Баланс",              metrics.balance_score,
         "сред. 3х пропорций",         "10.0"),
    ]
    st.append(_params_table(params))
    st.append(Spacer(1, 5*mm))

    # Измерения
    st += _section("АНТРОПОМЕТРИЧЕСКИЕ ИЗМЕРЕНИЯ")
    mrows = [
        ["Ширина лица",         f"{metrics.face_width:.0f}",   "Высота лица",        f"{metrics.face_height:.0f}"],
        ["Лев. глаз (шир.)",    f"{metrics.left_eye_width:.1f}","Прав. глаз (шир.)", f"{metrics.right_eye_width:.1f}"],
        ["Ширина носа",         f"{metrics.nose_width:.1f}",   "Ширина рта",         f"{metrics.mouth_width:.1f}"],
        ["МЗР",                 f"{metrics.interpupillary_distance:.1f}","МЗР/лицо", f"{ipr}"],
        ["Верхняя треть",       f"{metrics.upper_third:.1f}",  "Верхняя, %",         f"{up}%"],
        ["Средняя треть",       f"{metrics.middle_third:.1f}", "Средняя, %",         f"{mi}%"],
        ["Нижняя треть",        f"{metrics.lower_third:.1f}",  "Нижняя, %",          f"{lo}%"],
    ]
    st.append(_meas_table(mrows))
    st.append(Spacer(1, 5*mm))

    # Советы
    st += _section("ПЕРСОНАЛЬНЫЕ СОВЕТЫ — ВНЕШНОСТЬ И УХОД")
    for emoji, title, text in _advice(metrics):
        st.append(_advice_card(emoji, title, text))
        st.append(Spacer(1, 3*mm))

    # Шкала
    st.append(Spacer(1, 2*mm))
    st.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=2*mm))
    st.append(Paragraph("ШКАЛА ОЦЕНОК", _s("sc", fontName=BOLD, fontSize=10, textColor=GOLDB,
                                            spaceAfter=2*mm)))
    scale = [
        ("SSS", "9.5+", "Легендарная"),
        ("SS",  "9.0+", "Исключительная"),
        ("S",   "8.5+", "Высокая привлекательность"),
        ("A+",  "8.0+", "Выше среднего"),
        ("A",   "7.0+", "Привлекательный"),
        ("B",   "6.0+", "Чуть выше нормы"),
        ("C",   "5.0+", "Средний"),
        ("D",   "4.0+", "Ниже среднего"),
        ("E",   "<4.0", "Требует работы"),
    ]
    scdata = [[
        Paragraph(g, _s(f"sg{i}", fontName=BOLD, fontSize=8, textColor=GOLDB, alignment=TA_CENTER)),
        Paragraph(v, _s(f"sv{i}", fontSize=8, textColor=TEXT, alignment=TA_CENTER)),
        Paragraph(l, _s(f"sl{i}", fontSize=8, textColor=DIM)),
    ] for i, (g, v, l) in enumerate(scale)]
    sctbl = Table(scdata, colWidths=[20*mm, 22*mm, 62*mm]*3 if len(scale) == 9 else None,
                  hAlign="LEFT")
    # arrange 3 per row
    rows3 = [scale[i:i+3] for i in range(0, len(scale), 3)]
    flat = []
    for row in rows3:
        cells = []
        for g, v, l in row:
            cells += [
                Paragraph(g, _s("sg", fontName=BOLD, fontSize=8, textColor=GOLDB, alignment=TA_CENTER)),
                Paragraph(v, _s("sv", fontSize=8, textColor=TEXT, alignment=TA_CENTER)),
                Paragraph(l, _s("sl", fontSize=8, textColor=DIM)),
            ]
        while len(cells) < 9:
            cells.append(Paragraph("", _s("se", fontSize=8)))
        flat.append(cells)
    sc_tbl = Table(flat, colWidths=[18*mm, 18*mm, 38*mm]*3)
    sc_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [PANEL, PANEL2]),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]))
    st.append(sc_tbl)
    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph("Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
                        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER)))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


def generate_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    return generate_full_pdf(metrics, username)
