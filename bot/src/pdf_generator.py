"""
PDF-генератор Facedex — краткий и полный разбор.
Дизайн по образцу Face Aura с 20 метриками Фаркаса.
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
CYAN   = colors.HexColor("#64D2FF")

W, H  = A4
BODY  = W - 36*mm


def _sc(s): return GREEN if s >= 7.5 else (ORANGE if s >= 5.5 else RED)
def _sh(s): return "#4CAF50" if s >= 7.5 else ("#FF9800" if s >= 5.5 else "#F44336")
def _bar(s, n=20): filled = round(s / 10 * n); return "█" * filled + "░" * (n - filled)

def _level(s):
    if s >= 9.0: return "Высоко"
    if s >= 7.5: return "Выше среднего"
    if s >= 5.5: return "Среднее"
    if s >= 4.0: return "Ниже среднего"
    return "Низко"

def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, H - 3, W, 3, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 0, W, 2, fill=1, stroke=0)
    canvas.restoreState()

def _s(name, **kw):
    d = dict(fontName=REGULAR, textColor=TEXT, fontSize=10, leading=14, spaceAfter=0)
    d.update(kw)
    return ParagraphStyle(name, **d)

def _make_doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm)

def _tier_label(t):
    return {
        "HTN": "High Tier Normie",
        "MTN": "Mid Tier Normie",
        "LTN": "Low Tier Normie",
    }.get(t, t)

def _tier_sub(t):
    return {
        "HTN": "Топ 10% по геометрии лица",
        "MTN": "Выше среднего по геометрии лица",
        "LTN": "Средний диапазон геометрии лица",
    }.get(t, "")

def _photo(data, max_w=80*mm, max_h=90*mm):
    try:
        pil = PILImage.open(io.BytesIO(data))
        iw, ih = pil.size
        r = min(max_w / iw, max_h / ih)
        img = RLImage(io.BytesIO(data), width=iw*r, height=ih*r)
        img.hAlign = "CENTER"
        return img
    except Exception:
        return None


def _section(text):
    return [
        Spacer(1, 5*mm),
        Paragraph(text, _s("sh", fontName=BOLD, fontSize=11, textColor=GOLDB, spaceAfter=1*mm)),
        HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3*mm),
    ]


def _score_badge(score, grade, tier):
    """Бейдж с итоговым баллом, тиром и уровнем."""
    col = _sc(score)
    inner = Table([[
        Paragraph(f"{score:.2f}", _s("num", fontName=BOLD, fontSize=40, textColor=col,
                                     leading=46, alignment=TA_CENTER)),
        Paragraph("из 10", _s("of", fontSize=11, textColor=DIM, leading=14)),
    ]], colWidths=[42*mm, 20*mm])
    inner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    right_col = Table([[
        Paragraph(grade, _s("gr", fontName=BOLD, fontSize=12, textColor=TEXT, leading=16)),
    ], [
        Paragraph(f"{tier}  —  {_tier_label(tier)}",
                  _s("tr", fontSize=10, textColor=DIM, leading=14)),
    ], [
        Paragraph(_tier_sub(tier), _s("ts", fontSize=9, textColor=GOLD, leading=13)),
    ]], colWidths=[None])
    right_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    badge = Table([[inner, right_col]], colWidths=[65*mm, None])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT),
        ("BOX",           (0, 0), (-1, -1), 1.5, GOLD),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("LINEAFTER",     (0, 0), (0, -1), 1.5, GOLD),
    ]))
    return badge


def _mini_score_card(label, score):
    """Карточка метрики 3x3 сетки (для краткого разбора)."""
    col = _sc(score)
    lvl = _level(score)
    card = Table([[
        Paragraph(label, _s("cl", fontSize=9, textColor=DIM, leading=12, alignment=TA_CENTER)),
    ], [
        Paragraph(f'<font color="{_sh(score)}" size="22"><b>{score:.2f}</b></font>',
                  _s("cv", fontSize=22, fontName=BOLD, leading=26, alignment=TA_CENTER)),
    ], [
        Paragraph(lvl, _s("lv", fontSize=8, textColor=col, leading=11, alignment=TA_CENTER)),
    ]], colWidths=[None])
    card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PANEL),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    return card


def _metric_row(name, score, your_val, norm_val):
    bar = _bar(score)
    return [
        Paragraph(name, _s("rn", fontSize=9, textColor=TEXT, leading=13)),
        Paragraph(f'<font color="{_sh(score)}">{score:.2f}</font>',
                  _s("rs", fontName=BOLD, fontSize=13, alignment=TA_CENTER, leading=16)),
        Table([[
            Paragraph(f'<font name="Courier" size="7" color="#C9A84C">{bar}</font>',
                      _s("bar", fontSize=7, leading=10)),
            Paragraph(
                f'<font color="#6A6A80">Ваше: </font>{your_val}  '
                f'<font color="#6A6A80">Норма: </font>{norm_val}',
                _s("det", fontSize=7.5, textColor=TEXT, leading=11)),
        ]], colWidths=[None]),
    ]


def _params_table(rows):
    hdr = [
        Paragraph("Параметр",   _s("h0", fontName=BOLD, fontSize=9, textColor=GOLDB)),
        Paragraph("Балл",       _s("h1", fontName=BOLD, fontSize=9, textColor=GOLDB, alignment=TA_CENTER)),
        Paragraph("Бар  /  Ваше значение  →  Норма",
                  _s("h2", fontName=BOLD, fontSize=9, textColor=GOLDB)),
    ]
    tdata = [hdr] + [_metric_row(*r) for r in rows]
    COL = [66*mm, 18*mm, 90*mm]
    tbl = Table(tdata, colWidths=COL, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _meas_table(rows):
    hdr = [Paragraph(h, _s(f"mh{i}", fontName=BOLD, fontSize=9, textColor=GOLDB,
                            alignment=TA_LEFT if i % 2 == 0 else TA_CENTER))
           for i, h in enumerate(["Параметр", "Значение", "Параметр", "Значение"])]
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
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
    ]))
    return tbl


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
            ("BACKGROUND",   (0, 0), (-1, -1), PANEL),
            ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEAFTER",    (0, 0), (0, -1), 1.5, GOLD),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ])))


def _advice(m: FaceMetrics):
    tips = []

    # Кантальный тильт / глаза
    if m.canthal_tilt_degrees >= 5:
        tips.append(("👁", "Наклон глаз — хищный взгляд (hunter eyes)",
                     f"Угол {m.canthal_tilt_degrees:+.1f}° — выраженные hunter eyes. "
                     "Мьюинг и низкий % жира поддерживают этот эффект. "
                     "Избегай пуфа под глазами: меньше соли, больше сна."))
    elif m.canthal_tilt_degrees >= 0:
        tips.append(("👁", "Наклон глаз — нейтральный",
                     f"Угол {m.canthal_tilt_degrees:+.1f}°. "
                     "Убирай отёки под глазами: ледяной кубик или нефритовый роллер утром. "
                     "Мьюинг со временем поднимает средину лица."))
    else:
        tips.append(("👁", "Наклон глаз — зона работы",
                     f"Угол {m.canthal_tilt_degrees:+.1f}°. "
                     "Приоритет: убрать отёки (сон 8ч, нет соли, нет алкоголя). "
                     "Роллер из нефрита по утрам. Мьюинг обязателен."))

    # Симметрия
    if m.symmetry_score >= 8.5:
        tips.append(("🪞", "Симметрия — высокая",
                     "Не спи постоянно на одной стороне. "
                     "Следи за прикусом — неравномерный жевательный тонус смещает симметрию."))
    else:
        tips.append(("🪞", "Симметрия — есть асимметрия",
                     "Жуй поровну с обеих сторон. Сон на спине сохраняет симметрию. "
                     "Проверь прикус у ортодонта — это главная причина асимметрии лица."))

    # Скулы и челюсть
    if m.cheekbones_score >= 8:
        tips.append(("🦴", "Скулы и линия челюсти — выразительные",
                     "Стрижка с выбритыми висками (андеркат, тейпер) подчёркивает контур. "
                     "Держи % жира в теле ниже 15% — это делает скулы и челюсть рельефными."))
    else:
        tips.append(("💪", "Линия челюсти — есть потенциал",
                     "Три ключевых инструмента: 1) мьюинг, 2) жёсткая жвачка Falim ежедневно, "
                     "3) снижение % жира. Стрижка с длинными висками скрывает нечёткий контур."))

    # Нос
    if m.nose_score < 7:
        tips.append(("👃", "Нос — визуальная коррекция",
                     "Объём на висках визуально уменьшает нос. "
                     "Стрижка с более широкой верхней частью сужает восприятие носа. "
                     "Лёгкий контуринг носа работает даже у мужчин."))

    # Причёска / трети
    if m.facial_thirds_score < 7.5:
        tips.append(("✂️", "Причёска и трети лица",
                     "Трети лица корректируются причёской: высокий лоб — чёлка или зачёс вперёд; "
                     "низкий лоб — зачёс назад, объём на макушке."))
    else:
        tips.append(("✂️", "Причёска — подчеркни сильные стороны",
                     "Стрижка до ушей открывает скулы и подчёркивает челюсть. "
                     "Андеркат или тейпер по бокам добавляет «структуру» лицу."))

    # Кожа — всегда
    tips.append(("🧴", "Уход за кожей — базовый стек",
                 "SPF 30–50 каждый день (без исключений) — главный антивозрастной инструмент. "
                 "Увлажняющий крем утром и вечером. "
                 "Ретинол 0.025% на ночь раз в неделю — выравнивает текстуру и поры."))

    # Сон / образ жизни
    tips.append(("🌙", "Сон и образ жизни",
                 "7–9 часов сна снижают отёчность и улучшают кожу. "
                 "Вода 2.5–3 л/день убирает задержку жидкости в лице. "
                 "Ограничь сахар и переработанные продукты — кожа реагирует в течение 2–3 дней."))

    return tips


def _top_metrics(m: FaceMetrics):
    """Возвращает топ-3 сильных и топ-3 слабых метрик."""
    all_metrics = [
        ("Симметрия лица",          m.symmetry_score),
        ("Пропорции лица",          m.face_proportions_score),
        ("Вертикальный баланс",     m.vertical_balance_score),
        ("Баланс скул и челюсти",   m.cheekbones_score),
        ("Размер глаз",             m.eyes_score),
        ("Расст. между глазами",    m.eye_distance_score),
        ("Наклон глаз",             m.canthal_tilt_score),
        ("Ширина носа",             m.nose_score),
        ("Ширина рта",              m.lips_score),
        ("Длина носа",              m.nose_length_score),
        ("Длина подбородка",        m.chin_length_score),
        ("Контур подбородка",       m.chin_contour_score),
        ("Нос к ширине рта",        m.nose_to_mouth_score),
        ("Биокулярная ширина",      m.biocular_score),
        ("Ширина лба",              m.forehead_score),
        ("Полнота губ",             m.lip_fullness_score),
        ("Пропорции губ",           m.lip_ratio_score),
        ("Челюсть к ширине рта",    m.jaw_to_mouth_score),
        ("Форма глаз",              m.eye_shape_score),
        ("Высота бровей",           m.brow_height_score),
    ]
    srt = sorted(all_metrics, key=lambda x: x[1], reverse=True)
    return srt[:3], srt[-3:]


# ════════════════════════════════════════════════════════════════════════════
#  КРАТКИЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_brief_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st  = []

    # Шапка
    st.append(Paragraph("FACEDEX",
                         _s("t", fontName=BOLD, fontSize=30, textColor=GOLD,
                            alignment=TA_CENTER, spaceAfter=0)))
    st.append(Paragraph("Краткий математический разбор геометрии твоего лица.",
                         _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER, spaceAfter=2*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5*mm))

    # Фото (аннотированное)
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image, max_w=72*mm, max_h=84*mm)
        if ph:
            st.append(ph)
            st.append(Spacer(1, 4*mm))

    # Бейдж
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 6*mm))

    # Топ сильных и слабых
    strong, weak = _top_metrics(metrics)
    st += _section("ПРОФИЛЬ МЕТРИК")
    top_row = [[
        Paragraph("Топ-3 сильных метрики", _s("th", fontName=BOLD, fontSize=9, textColor=GOLDB)),
        Paragraph("Топ-3 зоны потенциала", _s("tw", fontName=BOLD, fontSize=9, textColor=DIM)),
    ]]
    for i in range(3):
        sn, ss = strong[i]
        wn, ws = weak[i]
        top_row.append([
            Paragraph(f'● {sn} — <font color="{_sh(ss)}">{ss:.2f}</font>',
                      _s("ts", fontSize=9, textColor=TEXT, leading=14)),
            Paragraph(f'● {wn} — <font color="{_sh(ws)}">{ws:.2f}</font>',
                      _s("tw2", fontSize=9, textColor=TEXT, leading=14)),
        ])
    top_tbl = Table(top_row, colWidths=[BODY / 2 - 3*mm, BODY / 2 - 3*mm])
    top_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER),
        ("BACKGROUND",    (0, 1), (-1, -1), PANEL),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEAFTER",     (0, 0), (0, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    st.append(top_tbl)
    st.append(Spacer(1, 6*mm))

    # Сетка 3×3 с 9 метриками
    st += _section("ОЦЕНКА ПО КЛЮЧЕВЫМ ПАРАМЕТРАМ")
    cards = [
        ("Симметрия",     metrics.symmetry_score),
        ("Верт. баланс",  metrics.vertical_balance_score),
        ("Скулы / чел.",  metrics.cheekbones_score),
        ("Размер глаз",   metrics.eyes_score),
        ("Наклон глаз",   metrics.canthal_tilt_score),
        ("Ширина носа",   metrics.nose_score),
        ("Полнота губ",   metrics.lip_fullness_score),
        ("Контур чел.",   metrics.chin_contour_score),
        ("Высота бровей", metrics.brow_height_score),
    ]
    rows_3 = [cards[i:i+3] for i in range(0, 9, 3)]
    grid_data = []
    for row in rows_3:
        grid_data.append([_mini_score_card(lbl, sc) for lbl, sc in row])
    cell_w = BODY / 3 - 2*mm
    grid = Table(grid_data, colWidths=[cell_w, cell_w, cell_w])
    grid.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ]))
    st.append(grid)
    st.append(Spacer(1, 6*mm))

    # Подсказка — апсейл к полному
    hint = Table([[Paragraph(
        "📊  Краткий разбор — лишь верхушка.\n"
        "Получи <b>Полный разбор на 25 страниц</b>: 20 метрик по нормам Лесли Фаркаса, "
        "детальное объяснение каждой метрики и конкретные шаги по улучшению внешности.",
        _s("hint", fontSize=9, textColor=DIM, leading=14)
    )]], colWidths=[BODY])
    hint.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), PANEL),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
    ]))
    st.append(KeepTogether(hint))
    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER)))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  ПОЛНЫЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_full_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    d   = metrics.details or {}
    fw  = metrics.face_width or 1
    fh  = metrics.face_height or 1
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st  = []

    # ── Обложка ──────────────────────────────────────────────────────────────
    st.append(Paragraph("FACEDEX",
                         _s("t", fontName=BOLD, fontSize=30, textColor=GOLD,
                            alignment=TA_CENTER, spaceAfter=0)))
    st.append(Paragraph("Полный математический разбор геометрии твоего лица.",
                         _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER, spaceAfter=2*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5*mm))

    # Фото
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image, max_w=80*mm, max_h=92*mm)
        if ph:
            st.append(ph)
            st.append(Spacer(1, 4*mm))

    # Бейдж
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 4*mm))

    # Общее впечатление
    strong, weak = _top_metrics(metrics)
    strong_str = ", ".join(n for n, _ in strong)
    weak_str   = ", ".join(n for n, _ in weak)

    intro_tbl = Table([[Paragraph(
        "<b>ОБЩЕЕ ВПЕЧАТЛЕНИЕ</b>",
        _s("ith", fontName=BOLD, fontSize=10, textColor=GOLDB, leading=14)),
    ], [Paragraph(
        f"Сильные стороны: {strong_str}. "
        f"Зоны потенциала: {weak_str}.",
        _s("itb", fontSize=9, textColor=TEXT, leading=14)),
    ]], colWidths=[BODY])
    intro_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), ACCENT),
        ("BOX",          (0, 0), (-1, -1), 0.6, GOLD),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))
    st.append(intro_tbl)
    st.append(Spacer(1, 4*mm))

    # ── Профиль метрик (топ/слабые) ──────────────────────────────────────────
    st += _section("ПРОФИЛЬ МЕТРИК")
    top_row = [[
        Paragraph("Топ-3 сильных метрики", _s("th", fontName=BOLD, fontSize=9, textColor=GOLDB)),
        Paragraph("Топ-3 зоны потенциала", _s("tw", fontName=BOLD, fontSize=9, textColor=DIM)),
    ]]
    for i in range(3):
        sn, ss = strong[i]
        wn, ws = weak[i]
        top_row.append([
            Paragraph(f'● {sn} — <font color="{_sh(ss)}">{ss:.2f}</font>',
                      _s("ts", fontSize=9, textColor=TEXT, leading=14)),
            Paragraph(f'● {wn} — <font color="{_sh(ws)}">{ws:.2f}</font>',
                      _s("tw2", fontSize=9, textColor=TEXT, leading=14)),
        ])
    top_tbl = Table(top_row, colWidths=[BODY / 2 - 3*mm, BODY / 2 - 3*mm])
    top_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER),
        ("BACKGROUND",    (0, 1), (-1, -1), PANEL),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEAFTER",     (0, 0), (0, -1), 0.5, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    st.append(top_tbl)

    # Вклад каждой метрики — маленькая сетка
    st.append(Spacer(1, 4*mm))
    st.append(Paragraph("Вклад каждой метрики",
                         _s("mth", fontName=BOLD, fontSize=10, textColor=GOLDB, spaceAfter=2*mm)))
    all_20 = [
        ("Симметрия лица",       metrics.symmetry_score),
        ("Длина подбородка",     metrics.chin_length_score),
        ("Пропорции лица",       metrics.face_proportions_score),
        ("Контур подбородка",    metrics.chin_contour_score),
        ("Вертикальный баланс",  metrics.vertical_balance_score),
        ("Нос к ширине рта",     metrics.nose_to_mouth_score),
        ("Баланс скул и чел.",   metrics.cheekbones_score),
        ("Биокулярная ширина",   metrics.biocular_score),
        ("Размер глаз",          metrics.eyes_score),
        ("Ширина лба",           metrics.forehead_score),
        ("Расст. между глазами", metrics.eye_distance_score),
        ("Полнота губ",          metrics.lip_fullness_score),
        ("Наклон глаз",          metrics.canthal_tilt_score),
        ("Пропорции губ",        metrics.lip_ratio_score),
        ("Ширина носа",          metrics.nose_score),
        ("Чел. к ширине рта",    metrics.jaw_to_mouth_score),
        ("Ширина рта",           metrics.lips_score),
        ("Форма глаз",           metrics.eye_shape_score),
        ("Длина носа",           metrics.nose_length_score),
        ("Высота бровей",        metrics.brow_height_score),
    ]
    contrib_rows = []
    for i in range(0, 20, 2):
        n1, s1 = all_20[i]
        n2, s2 = all_20[i + 1]
        contrib_rows.append([
            Paragraph(n1, _s("cn", fontSize=8.5, textColor=TEXT, leading=12)),
            Paragraph(f'<font color="{_sh(s1)}">{s1:.2f}</font>',
                      _s("cv", fontName=BOLD, fontSize=8.5, leading=12, alignment=TA_CENTER)),
            Paragraph(n2, _s("cn2", fontSize=8.5, textColor=TEXT, leading=12)),
            Paragraph(f'<font color="{_sh(s2)}">{s2:.2f}</font>',
                      _s("cv2", fontName=BOLD, fontSize=8.5, leading=12, alignment=TA_CENTER)),
        ])
    cont_tbl = Table(contrib_rows, colWidths=[62*mm, 18*mm, 62*mm, 18*mm])
    cont_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEBEFORE",    (2, 0), (2, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    st.append(cont_tbl)

    # ── 20 метрик с нормами ───────────────────────────────────────────────────
    st += _section("ОЦЕНКА ПО 20 ПАРАМЕТРАМ")

    hw   = round(d.get("face_hw_ratio", 0), 3)
    vb   = round(d.get("vert_balance", 0), 3)
    cj   = round(d.get("cheek_jaw_ratio", 0), 3)
    ef   = round(d.get("nose_to_face", metrics.left_eye_width / fw), 3)
    ief  = round(d.get("inner_eye_to_face", 0), 3)
    cn   = round(d.get("canthal_norm", 0), 3)
    nf   = round(d.get("nose_to_face", 0), 3)
    mf   = round(d.get("mouth_to_face", 0), 3)
    nl   = round(d.get("nose_len_ratio", 0), 3)
    cl   = round(d.get("chin_len_ratio", 0), 3)
    cc   = round(d.get("chin_contour", 0), 3)
    nm   = round(d.get("nose_to_mouth", 0), 3)
    bw   = round(d.get("biocular_width", 0), 3)
    fr   = round(d.get("forehead_ratio", 0), 3)
    lf   = round(d.get("lip_fullness", 0), 3)
    lr   = round(d.get("lip_ratio", 0), 3)
    jm   = round(d.get("jaw_to_mouth", 0), 3)
    es   = round(d.get("eye_shape", 0), 3)
    br   = round(d.get("brow_dist_ratio", 0), 3)

    params = [
        ("01  Симметрия лица",        metrics.symmetry_score,
         "Среднее по 3 парам",        "идеал: 10.0"),
        ("02  Пропорции лица",         metrics.face_proportions_score,
         f"В/Ш = {hw}",               "норма: 0.896"),
        ("03  Вертикальный баланс",    metrics.vertical_balance_score,
         f"Ср/Нижн = {vb}",           "норма: 0.728"),
        ("04  Баланс скул и чел.",     metrics.cheekbones_score,
         f"Скулы/Чел = {cj}",         "норма: 1.356"),
        ("05  Размер глаз",            metrics.eyes_score,
         f"Гл/Лицо = {ef}",           "норма: 0.223"),
        ("06  Расст. между глазами",   metrics.eye_distance_score,
         f"МГ/Лицо = {ief}",          "норма: 0.271"),
        ("07  Наклон глаз",            metrics.canthal_tilt_score,
         f"Угол {metrics.canthal_tilt_degrees:+.1f}°",  "+5° … +10°"),
        ("08  Ширина носа",            metrics.nose_score,
         f"Нос/Лицо = {nf}",          "норма: 0.234"),
        ("09  Ширина рта",             metrics.lips_score,
         f"Рот/Лицо = {mf}",          "норма: 0.403"),
        ("10  Длина носа",             metrics.nose_length_score,
         f"Дл.нос/Лицо = {nl}",       "норма: 0.421"),
        ("11  Длина подбородка",       metrics.chin_length_score,
         f"Подб/Лицо = {cl}",         "норма: 0.283"),
        ("12  Контур подбородка",      metrics.chin_contour_score,
         f"Угол сужения = {cc}",      "норма: 0.630"),
        ("13  Нос к ширине рта",       metrics.nose_to_mouth_score,
         f"Нос/Рот = {nm}",           "норма: 0.583"),
        ("14  Биокулярная ширина",     metrics.biocular_score,
         f"БОК/Лицо = {bw}",          "норма: 0.713"),
        ("15  Ширина лба",             metrics.forehead_score,
         f"Лб/Лицо = {fr}",           "норма: 0.919"),
        ("16  Полнота губ",            metrics.lip_fullness_score,
         f"Выс/Шир = {lf}",           "норма: 0.347"),
        ("17  Пропорции губ",          metrics.lip_ratio_score,
         f"Верх/Ниж = {lr}",          "норма: 0.639"),
        ("18  Чел. к ширине рта",      metrics.jaw_to_mouth_score,
         f"Чел/Рот = {jm}",           "норма: 1.810"),
        ("19  Форма глаз",             metrics.eye_shape_score,
         f"Выс/Шир = {es}",           "норма: 0.285"),
        ("20  Высота бровей",          metrics.brow_height_score,
         f"Дист/Лицо = {br}",         "норма: 0.063"),
    ]
    st.append(_params_table(params))

    # ── Антропометрия ─────────────────────────────────────────────────────────
    up  = round(d.get("upper_third_pct", 0), 1)
    mi  = round(d.get("middle_third_pct", 0), 1)
    lo  = round(d.get("lower_third_pct", 0), 1)
    ipr = round(metrics.interpupillary_distance / fw, 3) if fw else 0

    st += _section("АНТРОПОМЕТРИЧЕСКИЕ ИЗМЕРЕНИЯ")
    mrows = [
        ["Ширина лица",       f"{metrics.face_width:.0f} пx",   "Высота лица",         f"{metrics.face_height:.0f} пx"],
        ["Лев. глаз (шир.)",  f"{metrics.left_eye_width:.1f}",  "Прав. глаз (шир.)",   f"{metrics.right_eye_width:.1f}"],
        ["Ширина носа",       f"{metrics.nose_width:.1f}",       "Ширина рта",          f"{metrics.mouth_width:.1f}"],
        ["МЗР",               f"{metrics.interpupillary_distance:.1f}", "МЗР/Лицо",    f"{ipr}"],
        ["Верхняя треть",     f"{metrics.upper_third:.1f}",     "Верхняя, %",           f"{up}%"],
        ["Средняя треть",     f"{metrics.middle_third:.1f}",    "Средняя, %",           f"{mi}%"],
        ["Нижняя треть",      f"{metrics.lower_third:.1f}",     "Нижняя, %",            f"{lo}%"],
    ]
    st.append(_meas_table(mrows))

    # ── Персональные советы ───────────────────────────────────────────────────
    st += _section("ПЕРСОНАЛЬНЫЕ СОВЕТЫ — ВНЕШНОСТЬ И УХОД")
    for emoji, title, text in _advice(metrics):
        st.append(_advice_card(emoji, title, text))
        st.append(Spacer(1, 3*mm))

    # ── Шкала оценок ──────────────────────────────────────────────────────────
    st.append(Spacer(1, 2*mm))
    st.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=2*mm))
    st.append(Paragraph("ШКАЛА ОЦЕНОК",
                         _s("sc", fontName=BOLD, fontSize=10, textColor=GOLDB, spaceAfter=2*mm)))
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
    rows3 = [scale[i:i+3] for i in range(0, len(scale), 3)]
    flat  = []
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
    sc_tbl = Table(flat, colWidths=[18*mm, 18*mm, 38*mm] * 3)
    sc_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    st.append(sc_tbl)
    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER)))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


def generate_pdf(metrics: FaceMetrics, username: str = "user") -> bytes:
    return generate_full_pdf(metrics, username)
