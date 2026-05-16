"""
PDF-генератор Facedex — два режима: краткий и полный разбор.
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage

from face_analyzer import FaceMetrics

# ── Цветовая палитра ─────────────────────────────────────────────────────────
BG        = colors.HexColor("#0B0B0F")
PANEL     = colors.HexColor("#16161C")
PANEL2    = colors.HexColor("#111116")
GOLD      = colors.HexColor("#C9A84C")
GOLD_LITE = colors.HexColor("#E8C96A")
TEXT      = colors.HexColor("#EDEDEF")
DIM       = colors.HexColor("#777788")
GREEN     = colors.HexColor("#4CAF50")
ORANGE    = colors.HexColor("#FF9800")
RED       = colors.HexColor("#F44336")
BLUE      = colors.HexColor("#64B5F6")
BORDER    = colors.HexColor("#2A2A36")

W, H = A4


def _score_color(s: float) -> str:
    if s >= 7.5:
        return "#4CAF50"
    elif s >= 5.5:
        return "#FF9800"
    else:
        return "#F44336"


def _bar(score: float, width=22) -> str:
    filled = round(score / 10 * width)
    return "█" * filled + "░" * (width - filled)


def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.restoreState()


def _make_doc(buf):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm,
    )


def _style(name, **kw):
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kw)


def _photo_flowable(landmark_image: bytes, max_w=88*mm, max_h=88*mm):
    try:
        pil = PILImage.open(io.BytesIO(landmark_image))
        iw, ih = pil.size
        ratio = min(max_w / iw, max_h / ih)
        rl = RLImage(io.BytesIO(landmark_image), width=iw*ratio, height=ih*ratio)
        rl.hAlign = "CENTER"
        return rl
    except Exception:
        return None


def _tier_desc(tier: str) -> str:
    return {
        "HTN": "High Tier Normie — высокий уровень привлекательности",
        "MTN": "Mid Tier Normie — средний уровень привлекательности",
        "LTN": "Low Tier Normie — уровень ниже среднего",
    }.get(tier, tier)


# ════════════════════════════════════════════════════════════════════════════
#  КРАТКИЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

def generate_brief_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)

    s_title  = _style("T", fontSize=26, textColor=GOLD, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=1*mm)
    s_sub    = _style("Sub", fontSize=10, textColor=DIM, alignment=TA_CENTER, fontName="Helvetica", spaceAfter=5*mm)
    s_sec    = _style("Sec", fontSize=13, textColor=GOLD, fontName="Helvetica-Bold", spaceBefore=5*mm, spaceAfter=2*mm)
    s_body   = _style("Bo", fontSize=10, textColor=TEXT, fontName="Helvetica", leading=15, spaceAfter=2*mm)
    s_dim    = _style("Di", fontSize=8, textColor=DIM, fontName="Helvetica", leading=12)
    s_score  = _style("Sc", fontSize=46, textColor=GOLD, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_grade  = _style("Gr", fontSize=13, textColor=TEXT, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2*mm)
    s_tier   = _style("Ti", fontSize=11, textColor=BLUE, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4*mm)
    s_foot   = _style("Fo", fontSize=8, textColor=DIM, alignment=TA_CENTER, fontName="Helvetica")

    story = []

    # ── Шапка ───────────────────────────────────────────────────────────────
    story.append(Paragraph("FACEDEX", s_title))
    story.append(Paragraph(f"Краткий разбор лица  •  @{username}", s_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=4*mm))

    # ── Фото ────────────────────────────────────────────────────────────────
    if metrics.landmark_image:
        ph = _photo_flowable(metrics.landmark_image)
        if ph:
            story.append(ph)
            story.append(Spacer(1, 3*mm))

    # ── Общий балл ──────────────────────────────────────────────────────────
    story.append(Paragraph(f"{metrics.overall_score:.1f} / 10", s_score))
    story.append(Paragraph(metrics.grade, s_grade))
    story.append(Paragraph(f"🏷 Тир: {metrics.tier} — {_tier_desc(metrics.tier)}", s_tier))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3*mm))

    # ── Ключевые параметры ───────────────────────────────────────────────────
    story.append(Paragraph("ОЦЕНКА ПО КЛЮЧЕВЫМ ПАРАМЕТРАМ", s_sec))

    params = [
        ("👁  Глаза",         metrics.eyes_score),
        ("👃  Нос",           metrics.nose_score),
        ("👄  Губы",          metrics.lips_score),
        ("🦴  Скулы",         metrics.cheekbones_score),
        ("💪  Челюсть",       metrics.jaw_score),
        ("⬆️  Брови",        metrics.eyebrows_score),
        ("🪞  Симметрия",     metrics.symmetry_score),
        ("⚖️  Баланс",       metrics.balance_score),
    ]

    tdata = [["Параметр", "Балл", "Визуализация"]]
    for name, sc in params:
        col = _score_color(sc)
        tdata.append([
            Paragraph(name, _style("pc", fontSize=9, textColor=TEXT, fontName="Helvetica", leading=12)),
            Paragraph(f'<font color="{col}" size="11"><b>{sc:.1f}</b></font>',
                      _style("ps", alignment=TA_CENTER, fontName="Helvetica-Bold")),
            Paragraph(f'<font face="Courier" size="7" color="#C9A84C">{_bar(sc)}</font>',
                      _style("pb", fontName="Courier")),
        ])

    tbl = Table(tdata, colWidths=[52*mm, 22*mm, 84*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1,  0), BG),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [PANEL, PANEL2]),
        ("TEXTCOLOR",    (0, 0), (-1,  0), GOLD),
        ("FONTNAME",     (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1,  0), 9),
        ("GRID",         (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    # ── Итог ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3*mm))
    story.append(Paragraph(
        "Хочешь узнать больше? <b>Полный разбор</b> включает 20 метрик, сравнение с нормами "
        "Лесли Фаркаса, визуализацию измерений и персональные советы по улучшению.",
        _style("hint", fontSize=9, textColor=DIM, fontName="Helvetica", leading=13),
    ))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=2*mm))
    story.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        s_foot,
    ))

    doc.build(story, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
#  ПОЛНЫЙ РАЗБОР
# ════════════════════════════════════════════════════════════════════════════

# Нормы Лесли Фаркаса (лицевая антропометрия, мужчины)
FARKAS_NORMS = {
    "Соотношение высота/ширина лица (φ)": (1.618, "≈ 1.618"),
    "Ширина глаза / ширина лица":         (0.200, "≈ 0.200 (1/5)"),
    "Ширина носа / ширина лица":          (0.200, "≈ 0.200 (1/5)"),
    "Ширина рта / МЗР":                   (1.000, "≈ 1.000"),
    "Челюсть / скулы":                    (0.750, "≈ 0.750"),
    "Верхняя треть / высота лица":        (0.333, "≈ 33%"),
    "Средняя треть / высота лица":        (0.333, "≈ 33%"),
    "Нижняя треть / высота лица":         (0.333, "≈ 33%"),
    "Кантальный тильт":                   (5.0,   "+5°–+10°"),
    "МЗР / ширина лица":                  (0.400, "≈ 0.400"),
}


def generate_full_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)

    s_title  = _style("T",  fontSize=26, textColor=GOLD, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=1*mm)
    s_sub    = _style("Su", fontSize=10, textColor=DIM,  alignment=TA_CENTER, fontName="Helvetica",       spaceAfter=5*mm)
    s_sec    = _style("Se", fontSize=13, textColor=GOLD, fontName="Helvetica-Bold", spaceBefore=5*mm, spaceAfter=2*mm)
    s_body   = _style("Bo", fontSize=10, textColor=TEXT, fontName="Helvetica", leading=15, spaceAfter=2*mm)
    s_dim    = _style("Di", fontSize=8,  textColor=DIM,  fontName="Helvetica", leading=12)
    s_score  = _style("Sc", fontSize=44, textColor=GOLD, alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_grade  = _style("Gr", fontSize=13, textColor=TEXT, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2*mm)
    s_tier   = _style("Ti", fontSize=11, textColor=BLUE, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4*mm)
    s_foot   = _style("Fo", fontSize=8,  textColor=DIM,  alignment=TA_CENTER, fontName="Helvetica")

    story = []

    # ── Шапка ───────────────────────────────────────────────────────────────
    story.append(Paragraph("FACEDEX", s_title))
    story.append(Paragraph(f"Полный разбор лица  •  @{username}", s_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=4*mm))

    # ── Фото ────────────────────────────────────────────────────────────────
    if metrics.landmark_image:
        ph = _photo_flowable(metrics.landmark_image)
        if ph:
            story.append(ph)
            story.append(Spacer(1, 3*mm))

    # ── Общий балл ──────────────────────────────────────────────────────────
    story.append(Paragraph(f"{metrics.overall_score:.1f} / 10", s_score))
    story.append(Paragraph(metrics.grade, s_grade))
    story.append(Paragraph(f"🏷 Тир: {metrics.tier} — {_tier_desc(metrics.tier)}", s_tier))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3*mm))

    # ── Расширенные параметры ────────────────────────────────────────────────
    story.append(Paragraph("ОЦЕНКА ПО КЛЮЧЕВЫМ ПАРАМЕТРАМ", s_sec))

    all_params = [
        ("📐  Золотое сечение (φ)", metrics.golden_ratio_score,
         f"H/W = {metrics.details.get('face_hw_ratio', 0):.3f} (идеал φ=1.618)"),
        ("🪞  Симметрия",           metrics.symmetry_score,
         f"Глаза: {metrics.details.get('eye_symmetry',0):.1f}  Скулы: {metrics.details.get('cheek_symmetry',0):.1f}  Рот: {metrics.details.get('mouth_symmetry',0):.1f}"),
        ("📏  Трети лица",          metrics.facial_thirds_score,
         f"Верх: {metrics.details.get('upper_third_pct',0):.1f}%  Сред: {metrics.details.get('middle_third_pct',0):.1f}%  Низ: {metrics.details.get('lower_third_pct',0):.1f}%"),
        ("👁  Кантальный тильт",   metrics.canthal_tilt_score,
         f"Угол: {metrics.canthal_tilt_degrees:+.1f}° (идеал +5°–+10°)"),
        ("💪  Челюсть",            metrics.jaw_score,
         f"Челюсть/скулы: {metrics.details.get('jaw_to_cheek_ratio',0):.3f} (идеал ≈0.75)"),
        ("👁  Глаза",              metrics.eyes_score,
         "Ширина глаза относительно ширины лица"),
        ("👃  Нос",                metrics.nose_score,
         "Ширина носа относительно ширины лица"),
        ("👄  Губы",               metrics.lips_score,
         f"Рот/МЗР: {metrics.details.get('ipd_to_face_ratio',0):.3f}"),
        ("🦴  Скулы",              metrics.cheekbones_score,
         f"Скулы/челюсть: {metrics.details.get('cheek_jaw_ratio',0):.3f} (идеал ≈1.30)"),
        ("⬆️  Брови",             metrics.eyebrows_score,
         "Позиция и высота надбровных дуг"),
        ("⚖️  Баланс",            metrics.balance_score,
         "Общая гармония пропорций"),
    ]

    tdata = [["Параметр", "Балл", "Визуализация", "Детали"]]
    for name, sc, detail in all_params:
        col = _score_color(sc)
        tdata.append([
            Paragraph(name, _style("pc", fontSize=9, textColor=TEXT, fontName="Helvetica", leading=12)),
            Paragraph(f'<font color="{col}" size="11"><b>{sc:.1f}</b></font>',
                      _style("ps", alignment=TA_CENTER, fontName="Helvetica-Bold")),
            Paragraph(f'<font face="Courier" size="7" color="#C9A84C">{_bar(sc, 16)}</font>',
                      _style("pb", fontName="Courier")),
            Paragraph(detail, _style("pd", fontSize=8, textColor=DIM, fontName="Helvetica", leading=11)),
        ])

    tbl = Table(tdata, colWidths=[46*mm, 18*mm, 46*mm, 48*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), BG),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("TEXTCOLOR",     (0, 0), (-1,  0), GOLD),
        ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1,  0), 9),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    # ── Измерения ────────────────────────────────────────────────────────────
    story.append(Paragraph("АНТРОПОМЕТРИЧЕСКИЕ ИЗМЕРЕНИЯ", s_sec))

    mdata = [
        ["Параметр", "Значение", "Параметр", "Значение"],
        ["Ширина лица (пкс)", f"{metrics.face_width:.0f}",     "Высота лица (пкс)", f"{metrics.face_height:.0f}"],
        ["Лев. глаз (шир.)",  f"{metrics.left_eye_width:.1f}", "Прав. глаз (шир.)", f"{metrics.right_eye_width:.1f}"],
        ["Ширина носа",        f"{metrics.nose_width:.1f}",     "Ширина рта",         f"{metrics.mouth_width:.1f}"],
        ["МЗР",                f"{metrics.interpupillary_distance:.1f}", "МЗР / лицо", f"{metrics.details.get('ipd_to_face_ratio',0):.3f}"],
        ["Верхняя треть",      f"{metrics.upper_third:.1f}",   "Верхняя, %", f"{metrics.details.get('upper_third_pct',0):.1f}%"],
        ["Средняя треть",      f"{metrics.middle_third:.1f}",  "Средняя, %", f"{metrics.details.get('middle_third_pct',0):.1f}%"],
        ["Нижняя треть",       f"{metrics.lower_third:.1f}",   "Нижняя, %", f"{metrics.details.get('lower_third_pct',0):.1f}%"],
    ]

    mtbl = Table(mdata, colWidths=[48*mm, 28*mm, 48*mm, 28*mm])
    mtbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), BG),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("TEXTCOLOR",     (0, 0), (-1,  0), GOLD),
        ("TEXTCOLOR",     (0, 1), (-1, -1), TEXT),
        ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("ALIGN",         (3, 0), (3, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(mtbl)
    story.append(Spacer(1, 5*mm))

    # ── Нормы Фаркаса ────────────────────────────────────────────────────────
    story.append(Paragraph("СРАВНЕНИЕ С НОРМАМИ ЛЕСЛИ ФАРКАСА", s_sec))
    story.append(Paragraph(
        "Нормативные значения из исследования лицевой антропометрии "
        "Лесли Фаркаса — наиболее цитируемого в эстетической хирургии.",
        _style("fn", fontSize=9, textColor=DIM, fontName="Helvetica", leading=13, spaceAfter=3*mm),
    ))

    measured = {
        "Соотношение высота/ширина лица (φ)":  metrics.details.get("face_hw_ratio", 0),
        "Ширина глаза / ширина лица":           metrics.left_eye_width / metrics.face_width if metrics.face_width else 0,
        "Ширина носа / ширина лица":            metrics.nose_width / metrics.face_width if metrics.face_width else 0,
        "Ширина рта / МЗР":                     metrics.mouth_width / metrics.interpupillary_distance if metrics.interpupillary_distance else 0,
        "Челюсть / скулы":                      metrics.details.get("jaw_to_cheek_ratio", 0),
        "Верхняя треть / высота лица":          metrics.details.get("upper_third_pct", 0) / 100,
        "Средняя треть / высота лица":          metrics.details.get("middle_third_pct", 0) / 100,
        "Нижняя треть / высота лица":           metrics.details.get("lower_third_pct", 0) / 100,
        "Кантальный тильт":                     metrics.canthal_tilt_degrees,
        "МЗР / ширина лица":                    metrics.details.get("ipd_to_face_ratio", 0),
    }

    fdata = [["Метрика", "Норма (Фаркас)", "Твоё значение", "Δ"]]
    for metric, (ideal, label) in FARKAS_NORMS.items():
        val = measured.get(metric, 0)
        delta = val - ideal
        sign = "+" if delta >= 0 else ""
        fdata.append([
            Paragraph(metric, _style("fm", fontSize=8, textColor=TEXT, fontName="Helvetica", leading=11)),
            Paragraph(label,  _style("fn", fontSize=8, textColor=DIM,  fontName="Helvetica")),
            Paragraph(f"{val:.3f}", _style("fv", fontSize=8, textColor=TEXT, fontName="Helvetica-Bold")),
            Paragraph(f"{sign}{delta:.3f}", _style("fd", fontSize=8,
                      textColor=colors.HexColor("#4CAF50") if abs(delta) < ideal * 0.08 else colors.HexColor("#FF9800"),
                      fontName="Helvetica-Bold")),
        ])

    ftbl = Table(fdata, colWidths=[68*mm, 38*mm, 34*mm, 18*mm])
    ftbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), BG),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PANEL, PANEL2]),
        ("TEXTCOLOR",     (0, 0), (-1,  0), GOLD),
        ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1,  0), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(ftbl)
    story.append(Spacer(1, 5*mm))

    # ── Советы ───────────────────────────────────────────────────────────────
    story.append(Paragraph("ПЕРСОНАЛЬНЫЕ СОВЕТЫ ПО LOOKSMAXXING", s_sec))
    story.append(HRFlowable(width="100%", thickness=0.4, color=BORDER, spaceAfter=3*mm))

    for title, text in _get_advice(metrics):
        story.append(Paragraph(
            f'<font color="#C9A84C"><b>{title}</b></font> — {text}',
            s_body,
        ))

    # ── Шкала оценок ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.4, color=BORDER, spaceAfter=2*mm))
    story.append(Paragraph("ШКАЛА ОЦЕНОК", s_sec))
    story.append(Paragraph(
        "SSS (9.5+) Легендарная внешность  •  SS (9.0+) Исключительная красота  •  "
        "S (8.5+) Высокая привлекательность  •  A+ (8.0+) Выше среднего  •  "
        "A (7.0+) Привлекательный  •  B (6.0+) Чуть выше нормы  •  "
        "C (5.0+) Средний  •  D (4.0+) Ниже среднего  •  E (<4.0) Требует работы",
        _style("sc2", fontSize=8, textColor=DIM, fontName="Helvetica", leading=13),
    ))

    # ── Подвал ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=2*mm))
    story.append(Paragraph(
        "Facedex  •  Математический анализ гармонии лица  •  Только для развлечения",
        s_foot,
    ))

    doc.build(story, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


# ── Псевдоним для обратной совместимости ────────────────────────────────────
def generate_pdf(metrics: FaceMetrics, username: str = "Пользователь") -> bytes:
    return generate_full_pdf(metrics, username)


# ── Советы ──────────────────────────────────────────────────────────────────
def _get_advice(m: FaceMetrics):
    items = []

    if m.golden_ratio_score >= 8:
        items.append(("Золотое сечение", "Твои пропорции близки к золотому сечению (φ=1.618). Поддерживай текущую форму лица, избегай отёков: минимизируй соль и алкоголь."))
    elif m.golden_ratio_score >= 6:
        items.append(("Золотое сечение", "Пропорции неплохие, но есть запас. Мьюинг (правильное положение языка) и жевание жёсткой мастики помогают со временем улучшить форму."))
    else:
        items.append(("Золотое сечение", "Пропорции заметно отличаются от идеала. Проконсультируйся с ортодонтом — иногда прикус сильно влияет на форму лица."))

    if m.symmetry_score >= 8:
        items.append(("Симметрия", "Отличная симметрия — признак хорошей генетики. Следи за осанкой и позой сна: привычка спать на одной стороне ухудшает симметрию."))
    elif m.symmetry_score >= 6:
        items.append(("Симметрия", "Средняя симметрия. Старайся жевать равномерно с обеих сторон и спать на спине — это постепенно выравнивает лицо."))
    else:
        items.append(("Симметрия", "Заметная асимметрия. Часто причина — неправильная осанка или привычка жевать только с одной стороны. Исправляй осознанно."))

    if m.canthal_tilt_degrees >= 5:
        items.append(("Кантальный тильт", f"Положительный тильт {m.canthal_tilt_degrees:+.1f}° — «охотничьи глаза», высоко ценятся. Поддерживай мьюинг и избегай отёков под глазами."))
    elif m.canthal_tilt_degrees >= 0:
        items.append(("Кантальный тильт", f"Нейтральный тильт ({m.canthal_tilt_degrees:+.1f}°). Снижение отёчности и правильная осанка помогают визуально улучшить эффект."))
    else:
        items.append(("Кантальный тильт", f"Отрицательный тильт ({m.canthal_tilt_degrees:+.1f}°). Косметически это корректируется кантопексией; дома помогает снижение отёков и уход за кожей вокруг глаз."))

    if m.jaw_score >= 8:
        items.append(("Челюсть", "Чёткая линия челюсти — большой плюс. Поддерживай низкий процент жира, чтобы сохранять чёткость контура."))
    else:
        items.append(("Челюсть", "Для улучшения линии челюсти: снижай процент жира, жуй мастику ежедневно (жвачка Falim или мастика), делай мьюинг."))

    items.append(("Уход за кожей", "Увлажняй кожу утром и вечером, используй SPF 30+ ежедневно — это одно из самых сильных воздействий на восприятие внешности."))
    items.append(("Сон и питание", "7–9 часов сна снижают отёчность, улучшают текстуру кожи и поддерживают гормональный фон. Избегай сахара и переработанных продуктов."))

    return items
