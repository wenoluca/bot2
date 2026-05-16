"""
PDF-генератор Facedex — краткий и полный разбор.
Шрифт DejaVuSans — полная поддержка кириллицы.
"""
import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from face_analyzer import FaceMetrics

# ── Шрифты ───────────────────────────────────────────────────────────────────
_FONT_DIR  = os.path.join(os.path.dirname(__file__), "..", "assets")
_FONT_PATH = os.path.join(_FONT_DIR, "DejaVuSans.ttf")

pdfmetrics.registerFont(TTFont("DV",  _FONT_PATH))
pdfmetrics.registerFont(TTFont("DVB", _FONT_PATH))   # bold alias (same file, used for size)

REGULAR = "DV"
BOLD    = "DVB"

# ── Цвета ────────────────────────────────────────────────────────────────────
BG      = colors.HexColor("#0B0B0F")
PANEL   = colors.HexColor("#17171E")
PANEL2  = colors.HexColor("#111116")
GOLD    = colors.HexColor("#C9A84C")
GOLDB   = colors.HexColor("#E8C96A")
TEXT    = colors.HexColor("#EEEEF2")
DIM     = colors.HexColor("#6A6A80")
GREEN   = colors.HexColor("#4CAF50")
ORANGE  = colors.HexColor("#FF9800")
RED     = colors.HexColor("#F44336")
BLUE    = colors.HexColor("#64B5F6")
BORDER  = colors.HexColor("#28283A")
ACCENT  = colors.HexColor("#1E1E2C")

W, H = A4


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sc(s: float) -> colors.HexColor:
    return GREEN if s >= 7.5 else (ORANGE if s >= 5.5 else RED)


def _sc_hex(s: float) -> str:
    return "#4CAF50" if s >= 7.5 else ("#FF9800" if s >= 5.5 else "#F44336")


def _bar(score: float, w=24) -> str:
    n = round(score / 10 * w)
    return "█" * n + "░" * (w - n)


def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Тонкая золотая полоса сверху
    canvas.setFillColor(GOLD)
    canvas.rect(0, H - 3, W, 3, fill=1, stroke=0)
    canvas.restoreState()


def _s(name, **kw) -> ParagraphStyle:
    defaults = dict(fontName=REGULAR, textColor=TEXT, fontSize=10, leading=15, spaceAfter=2*mm)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


def _make_doc(buf):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=16*mm, bottomMargin=16*mm,
    )


def _photo(landmark_image: bytes, max_w=92*mm, max_h=92*mm):
    try:
        pil = PILImage.open(io.BytesIO(landmark_image))
        iw, ih = pil.size
        ratio = min(max_w / iw, max_h / ih)
        rl = RLImage(io.BytesIO(landmark_image), width=iw * ratio, height=ih * ratio)
        rl.hAlign = "CENTER"
        return rl
    except Exception:
        return None


def _tier_desc(tier: str) -> str:
    return {
        "HTN": "High Tier Normie — высокая привлекательность",
        "MTN": "Mid Tier Normie — средняя привлекательность",
        "LTN": "Low Tier Normie — ниже среднего",
    }.get(tier, tier)


def _section(text: str):
    """Заголовок секции с золотым разделителем."""
    return [
        Spacer(1, 5*mm),
        Paragraph(text, _s("sh", fontName=BOLD, fontSize=12, textColor=GOLDB,
                            spaceAfter=1*mm, borderPad=0)),
        HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3*mm),
    ]


def _score_badge(score: float, grade: str, tier: str):
    """Таблица-«бейдж» с итоговым баллом."""
    col = _sc(score)
    data = [[
        Paragraph(f"{score:.1f}/10",
                  _s("sb", fontName=BOLD, fontSize=40, textColor=col,
                     alignment=TA_CENTER, spaceAfter=0)),
        Paragraph(
            f"{grade}\n\n🏷 {tier}  —  {_tier_desc(tier)}",
            _s("sg", fontName=BOLD, fontSize=11, textColor=TEXT,
               leading=18, spaceAfter=0)),
    ]]
    tbl = Table(data, colWidths=[55*mm, None])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), ACCENT),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [6]),
        ("BOX",          (0, 0), (-1, -1), 1.5, GOLD),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _params_table(rows, wide=False):
    """Таблица параметров с цветными баллами и барами."""
    col_w = [50*mm, 20*mm, 52*mm, 36*mm] if wide else [54*mm, 20*mm, 84*mm]

    header = ["Параметр", "Балл", "Визуализация"] + (["Детали"] if wide else [])
    tdata = [
        [Paragraph(h, _s("th", fontName=BOLD, fontSize=9, textColor=GOLDB,
                          alignment=TA_CENTER if i > 0 else TA_LEFT, spaceAfter=0))
         for i, h in enumerate(header)]
    ]

    for row in rows:
        name, sc = row[0], row[1]
        detail   = row[2] if wide else None
        col = _sc_hex(sc)
        cells = [
            Paragraph(name, _s("rn", fontSize=9, textColor=TEXT, leading=13, spaceAfter=0)),
            Paragraph(f'<font color="{col}">{sc:.1f}</font>',
                      _s("rs", fontName=BOLD, fontSize=11, alignment=TA_CENTER, spaceAfter=0)),
            Paragraph(f'<font name="Courier" size="7" color="#C9A84C">{_bar(sc)}</font>',
                      _s("rb", fontSize=7, spaceAfter=0)),
        ]
        if wide and detail:
            cells.append(Paragraph(detail, _s("rd", fontSize=8, textColor=DIM, leading=11, spaceAfter=0)))
        tdata.append(cells)

    tbl = Table(tdata, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), colors.HexColor("#0D0D14")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _meas_table(data_rows):
    tdata = [[Paragraph(h, _s("mh", fontName=BOLD, fontSize=9, textColor=GOLDB,
                               alignment=TA_CENTER if i % 2 else TA_LEFT, spaceAfter=0))
              for i, h in enumerate(["Параметр", "Значение", "Параметр", "Значение"])]]
    for row in data_rows:
        tdata.append([
            Paragraph(str(row[0]), _s("ml", fontSize=9, textColor=TEXT, spaceAfter=0)),
            Paragraph(str(row[1]), _s("mv", fontName=BOLD, fontSize=9, textColor=GOLDB,
                                      alignment=TA_CENTER, spaceAfter=0)),
            Paragraph(str(row[2]), _s("mr", fontSize=9, textColor=TEXT, spaceAfter=0)),
            Paragraph(str(row[3]), _s("mw", fontName=BOLD, fontSize=9, textColor=GOLDB,
                                      alignment=TA_CENTER, spaceAfter=0)),
        ])
    tbl = Table(tdata, colWidths=[55*mm, 25*mm, 55*mm, 23*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#0D0D14")),
        ("ROWBACKGROUNDS",(0, 1), (-1,-1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1,-1), 0.5, GOLD),
        ("INNERGRID",     (0, 0), (-1,-1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1,-1), 4),
        ("BOTTOMPADDING", (0, 0), (-1,-1), 4),
        ("LEFTPADDING",   (0, 0), (-1,-1), 7),
    ]))
    return tbl


def _advice_block(title: str, text: str):
    outer = Table(
        [[Paragraph(title, _s("at", fontName=BOLD, fontSize=10, textColor=GOLDB,
                              spaceAfter=3)),
          Paragraph(text,  _s("ab", fontSize=9, textColor=TEXT, leading=14, spaceAfter=0))]],
        colWidths=[42*mm, None],
    )
    outer.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), PANEL),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER",    (0, 0), (0, -1), 1.5, GOLD),
    ]))
    return outer


# ════════════════════════════════════════════════════════════════════════════
#  КРАТКИЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_brief_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st = []

    # ── Шапка ───────────────────────────────────────────────────────────────
    st.append(Paragraph("FACEDEX", _s("t", fontName=BOLD, fontSize=28, textColor=GOLD,
                                      alignment=TA_CENTER, spaceAfter=1*mm)))
    st.append(Paragraph(f"Краткий разбор  •  @{username}",
                        _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER,
                           spaceAfter=4*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5*mm))

    # ── Фото ────────────────────────────────────────────────────────────────
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image)
        if ph:
            st.append(ph)
            st.append(Spacer(1, 4*mm))

    # ── Итоговый балл ───────────────────────────────────────────────────────
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 5*mm))

    # ── Ключевые параметры ──────────────────────────────────────────────────
    st += _section("ОЦЕНКА ПО КЛЮЧЕВЫМ ПАРАМЕТРАМ")
    params = [
        ("👁  Глаза",      metrics.eyes_score),
        ("👃  Нос",        metrics.nose_score),
        ("👄  Губы",       metrics.lips_score),
        ("🦴  Скулы",      metrics.cheekbones_score),
        ("💪  Челюсть",    metrics.jaw_score),
        ("↑   Брови",      metrics.eyebrows_score),
        ("🪞  Симметрия",  metrics.symmetry_score),
        ("⚖   Баланс",     metrics.balance_score),
    ]
    st.append(_params_table(params, wide=False))
    st.append(Spacer(1, 6*mm))

    # ── Подсказка ────────────────────────────────────────────────────────────
    st.append(Table(
        [[Paragraph(
            "Хочешь больше деталей?\n"
            "Полный разбор включает 20 метрик, нормы Лесли Фаркаса,\n"
            "визуализацию измерений и персональные советы.",
            _s("hint", fontSize=9, textColor=DIM, leading=14, spaceAfter=0)
        )]],
        colWidths=[W - 36*mm],
    ))

    st.append(Spacer(1, 5*mm))
    st.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER),
    ))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  ПОЛНЫЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

FARKAS = {
    "Высота / ширина лица (φ)":   (1.618, "≈ 1.618"),
    "Ширина глаза / лицо":        (0.200, "≈ 0.200"),
    "Ширина носа / лицо":         (0.200, "≈ 0.200"),
    "Ширина рта / МЗР":           (1.000, "≈ 1.000"),
    "Челюсть / скулы":            (0.750, "≈ 0.750"),
    "Верхняя треть, %":           (0.333, "≈ 33%"),
    "Средняя треть, %":           (0.333, "≈ 33%"),
    "Нижняя треть, %":            (0.333, "≈ 33%"),
    "Кантальный тильт (°)":       (5.0,   "+5°–+10°"),
    "МЗР / ширина лица":          (0.400, "≈ 0.400"),
}


def generate_full_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)
    st = []

    # ── Шапка ───────────────────────────────────────────────────────────────
    st.append(Paragraph("FACEDEX", _s("t", fontName=BOLD, fontSize=28, textColor=GOLD,
                                      alignment=TA_CENTER, spaceAfter=1*mm)))
    st.append(Paragraph(f"Полный разбор  •  @{username}",
                        _s("su", fontSize=10, textColor=DIM, alignment=TA_CENTER,
                           spaceAfter=4*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5*mm))

    # ── Фото ────────────────────────────────────────────────────────────────
    if metrics.landmark_image:
        ph = _photo(metrics.landmark_image)
        if ph:
            st.append(ph)
            st.append(Spacer(1, 4*mm))

    # ── Итоговый балл ───────────────────────────────────────────────────────
    st.append(_score_badge(metrics.overall_score, metrics.grade, metrics.tier))
    st.append(Spacer(1, 5*mm))

    # ── Расширенные параметры ────────────────────────────────────────────────
    st += _section("ОЦЕНКА ПО 11 ПАРАМЕТРАМ")
    all_params = [
        ("📐  Золотое сечение (φ)", metrics.golden_ratio_score,
         f"H/W={metrics.details.get('face_hw_ratio',0):.3f} (φ=1.618)"),
        ("🪞  Симметрия",           metrics.symmetry_score,
         f"Гл: {metrics.details.get('eye_symmetry',0):.1f} Ск: {metrics.details.get('cheek_symmetry',0):.1f} Рот: {metrics.details.get('mouth_symmetry',0):.1f}"),
        ("📏  Трети лица",          metrics.facial_thirds_score,
         f"В: {metrics.details.get('upper_third_pct',0):.1f}% С: {metrics.details.get('middle_third_pct',0):.1f}% Н: {metrics.details.get('lower_third_pct',0):.1f}%"),
        ("👁  Кантальный тильт",   metrics.canthal_tilt_score,
         f"Угол: {metrics.canthal_tilt_degrees:+.1f}° (идеал +5°–+10°)"),
        ("💪  Челюсть",            metrics.jaw_score,
         f"Чел/скулы: {metrics.details.get('jaw_to_cheek_ratio',0):.3f} (≈0.75)"),
        ("👁  Глаза",              metrics.eyes_score, "Ширина глаза / ширина лица"),
        ("👃  Нос",                metrics.nose_score, "Ширина носа / ширина лица"),
        ("👄  Губы",               metrics.lips_score,
         f"Рот/МЗР: {metrics.details.get('ipd_to_face_ratio',0):.3f}"),
        ("🦴  Скулы",              metrics.cheekbones_score,
         f"Ск/чел: {metrics.details.get('cheek_jaw_ratio',0):.3f} (≈1.30)"),
        ("↑   Брови",             metrics.eyebrows_score, "Позиция надбровных дуг"),
        ("⚖   Баланс",            metrics.balance_score,  "Общая гармония пропорций"),
    ]
    st.append(_params_table(all_params, wide=True))
    st.append(Spacer(1, 5*mm))

    # ── Измерения ────────────────────────────────────────────────────────────
    st += _section("АНТРОПОМЕТРИЧЕСКИЕ ИЗМЕРЕНИЯ")
    mrows = [
        ["Ширина лица (пкс)",  f"{metrics.face_width:.0f}",  "Высота лица (пкс)", f"{metrics.face_height:.0f}"],
        ["Лев. глаз (шир.)",   f"{metrics.left_eye_width:.1f}","Прав. глаз (шир.)",f"{metrics.right_eye_width:.1f}"],
        ["Ширина носа",         f"{metrics.nose_width:.1f}",   "Ширина рта",        f"{metrics.mouth_width:.1f}"],
        ["МЗР",                 f"{metrics.interpupillary_distance:.1f}", "МЗР / лицо", f"{metrics.details.get('ipd_to_face_ratio',0):.3f}"],
        ["Верхняя треть",       f"{metrics.upper_third:.1f}", "Верхняя, %", f"{metrics.details.get('upper_third_pct',0):.1f}%"],
        ["Средняя треть",       f"{metrics.middle_third:.1f}","Средняя, %", f"{metrics.details.get('middle_third_pct',0):.1f}%"],
        ["Нижняя треть",        f"{metrics.lower_third:.1f}", "Нижняя, %",  f"{metrics.details.get('lower_third_pct',0):.1f}%"],
    ]
    st.append(_meas_table(mrows))
    st.append(Spacer(1, 5*mm))

    # ── Нормы Фаркаса ────────────────────────────────────────────────────────
    st += _section("СРАВНЕНИЕ С НОРМАМИ ЛЕСЛИ ФАРКАСА")
    st.append(Paragraph(
        "Нормативные значения из наиболее цитируемого исследования лицевой антропометрии "
        "по Лесли Фаркасу, применяемого в эстетической хирургии.",
        _s("fn", fontSize=9, textColor=DIM, leading=13, spaceAfter=3*mm),
    ))

    measured = {
        "Высота / ширина лица (φ)":   metrics.details.get("face_hw_ratio", 0),
        "Ширина глаза / лицо":        metrics.left_eye_width / metrics.face_width if metrics.face_width else 0,
        "Ширина носа / лицо":         metrics.nose_width / metrics.face_width if metrics.face_width else 0,
        "Ширина рта / МЗР":           metrics.mouth_width / metrics.interpupillary_distance if metrics.interpupillary_distance else 0,
        "Челюсть / скулы":            metrics.details.get("jaw_to_cheek_ratio", 0),
        "Верхняя треть, %":           metrics.details.get("upper_third_pct", 0) / 100,
        "Средняя треть, %":           metrics.details.get("middle_third_pct", 0) / 100,
        "Нижняя треть, %":            metrics.details.get("lower_third_pct", 0) / 100,
        "Кантальный тильт (°)":       metrics.canthal_tilt_degrees,
        "МЗР / ширина лица":          metrics.details.get("ipd_to_face_ratio", 0),
    }

    fdata = [[Paragraph(h, _s(f"fh{i}", fontName=BOLD, fontSize=9, textColor=GOLDB,
                               alignment=TA_LEFT if i == 0 else TA_CENTER, spaceAfter=0))
              for i, h in enumerate(["Метрика", "Норма (Фаркас)", "Твоё значение", "Δ"])]]
    for metric, (ideal, label) in FARKAS.items():
        val = measured.get(metric, 0)
        delta = val - ideal
        sign = "+" if delta >= 0 else ""
        ok = abs(delta) < ideal * 0.08
        fdata.append([
            Paragraph(metric, _s("fm", fontSize=8, textColor=TEXT, leading=11, spaceAfter=0)),
            Paragraph(label,  _s("fl", fontSize=8, textColor=DIM, alignment=TA_CENTER, spaceAfter=0)),
            Paragraph(f"{val:.3f}", _s("fv", fontName=BOLD, fontSize=8, alignment=TA_CENTER, spaceAfter=0)),
            Paragraph(f"{sign}{delta:.3f}",
                      _s("fd", fontName=BOLD, fontSize=8, alignment=TA_CENTER,
                         textColor=GREEN if ok else ORANGE, spaceAfter=0)),
        ])

    ftbl = Table(fdata, colWidths=[68*mm, 38*mm, 32*mm, 20*mm])
    ftbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), colors.HexColor("#0D0D14")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
    ]))
    st.append(ftbl)
    st.append(Spacer(1, 5*mm))

    # ── Советы ───────────────────────────────────────────────────────────────
    st += _section("ПЕРСОНАЛЬНЫЕ СОВЕТЫ ПО LOOKSMAXXING")
    for title, text in _advice(metrics):
        st.append(_advice_block(title, text))
        st.append(Spacer(1, 3*mm))

    # ── Шкала ────────────────────────────────────────────────────────────────
    st.append(Spacer(1, 3*mm))
    st.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=2*mm))
    st.append(Paragraph("ШКАЛА ОЦЕНОК", _s("scl", fontName=BOLD, fontSize=10, textColor=GOLDB,
                                            spaceAfter=1*mm)))
    st.append(Paragraph(
        "SSS 9.5+  Легендарная  •  SS 9.0+  Исключительная  •  S 8.5+  Высокая  •  "
        "A+ 8.0+  Выше среднего  •  A 7.0+  Привлекательный  •  B 6.0+  Чуть выше нормы  •  "
        "C 5.0+  Средний  •  D 4.0+  Ниже среднего  •  E <4.0  Требует работы",
        _s("sc2", fontSize=8, textColor=DIM, leading=12),
    ))
    st.append(Spacer(1, 4*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER),
    ))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ── Псевдоним ────────────────────────────────────────────────────────────────
def generate_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    return generate_full_pdf(metrics, username)


# ── Советы ──────────────────────────────────────────────────────────────────
def _advice(m: FaceMetrics):
    tips = []
    if m.golden_ratio_score >= 8:
        tips.append(("Золотое сечение", "Пропорции близки к φ=1.618. Поддерживай форму лица — избегай отёков: меньше соли и алкоголя, больше воды."))
    elif m.golden_ratio_score >= 6:
        tips.append(("Золотое сечение", "Пропорции хорошие, но есть запас. Мьюинг и жевание жёсткой мастики (Falim, мастика Хиос) постепенно улучшают форму."))
    else:
        tips.append(("Золотое сечение", "Пропорции отличаются от идеала. Проконсультируйся с ортодонтом — прикус сильно влияет на форму лица."))

    if m.symmetry_score >= 8:
        tips.append(("Симметрия", "Отличная симметрия — признак хорошей генетики. Следи за осанкой и не спи постоянно на одной стороне."))
    else:
        tips.append(("Симметрия", "Жуй равномерно с обеих сторон и старайся спать на спине — это постепенно выравнивает лицо."))

    if m.canthal_tilt_degrees >= 5:
        tips.append(("Кантальный тильт", f"Положительный тильт {m.canthal_tilt_degrees:+.1f}° — «охотничьи глаза», высоко ценятся. Мьюинг и низкий % жира поддерживают этот эффект."))
    elif m.canthal_tilt_degrees >= 0:
        tips.append(("Кантальный тильт", f"Нейтральный тильт ({m.canthal_tilt_degrees:+.1f}°). Снижение отёчности и правильная осанка визуально улучшают ситуацию."))
    else:
        tips.append(("Кантальный тильт", f"Отрицательный тильт ({m.canthal_tilt_degrees:+.1f}°). Устрани отёки под глазами, используй роллер для лица и следи за осанкой."))

    if m.jaw_score >= 8:
        tips.append(("Челюсть", "Чёткая линия челюсти. Поддерживай низкий процент жира — это главный фактор видимости контура."))
    else:
        tips.append(("Челюсть", "Жуй мастику ежедневно, снижай % жира и делай мьюинг — это три главных метода для улучшения линии челюсти."))

    tips.append(("Уход за кожей", "SPF 30+ каждый день + увлажнение утром и вечером. Это одно из самых мощных воздействий на восприятие внешности."))
    tips.append(("Образ жизни", "7–9 ч сна снижают отёчность и улучшают кожу. Избегай сахара, переработанных продуктов и высокого потребления соли."))
    return tips
