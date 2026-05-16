import io
import math
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from face_analyzer import FaceMetrics


DARK_BG = colors.HexColor("#0D0D0D")
ACCENT = colors.HexColor("#C9A84C")  # gold
TEXT_LIGHT = colors.HexColor("#F0F0F0")
TEXT_DIM = colors.HexColor("#888888")
PANEL_BG = colors.HexColor("#1A1A1A")
GREEN = colors.HexColor("#4CAF50")
RED = colors.HexColor("#F44336")
ORANGE = colors.HexColor("#FF9800")
BLUE_ACCENT = colors.HexColor("#64B5F6")


def _score_color(score: float):
    if score >= 8.0:
        return GREEN
    elif score >= 6.0:
        return ORANGE
    else:
        return RED


def _score_bar_text(score: float, max_width=20) -> str:
    filled = round(score / 10 * max_width)
    return "█" * filled + "░" * (max_width - filled)


def generate_pdf(metrics: FaceMetrics, username: str = "User") -> bytes:
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    w, h = A4

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontSize=24,
        textColor=ACCENT,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=TEXT_DIM,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
        fontName="Helvetica",
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Normal"],
        fontSize=13,
        textColor=ACCENT,
        spaceAfter=3 * mm,
        spaceBefore=5 * mm,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=TEXT_LIGHT,
        spaceAfter=2 * mm,
        fontName="Helvetica",
        leading=14,
    )
    dim_style = ParagraphStyle(
        "Dim",
        parent=styles["Normal"],
        fontSize=9,
        textColor=TEXT_DIM,
        fontName="Helvetica",
        leading=13,
    )
    big_score_style = ParagraphStyle(
        "BigScore",
        parent=styles["Normal"],
        fontSize=42,
        textColor=ACCENT,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    grade_style = ParagraphStyle(
        "Grade",
        parent=styles["Normal"],
        fontSize=14,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=3 * mm,
    )

    story = []

    # ── Header ──────────────────────────────────────────────────
    story.append(Paragraph("LOOKSMAXXING ANALYSIS", title_style))
    story.append(Paragraph(f"Facial Harmony & Symmetry Report — @{username}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=5 * mm))

    # ── Annotated face image ─────────────────────────────────────
    if metrics.landmark_image:
        try:
            pil_img = PILImage.open(io.BytesIO(metrics.landmark_image))
            img_w, img_h = pil_img.size
            max_w = 90 * mm
            max_h = 90 * mm
            ratio = min(max_w / img_w, max_h / img_h)
            rl_img = RLImage(
                io.BytesIO(metrics.landmark_image),
                width=img_w * ratio,
                height=img_h * ratio,
            )
            rl_img.hAlign = "CENTER"
            story.append(rl_img)
            story.append(Spacer(1, 4 * mm))
        except Exception:
            pass

    # ── Overall Score ────────────────────────────────────────────
    story.append(Paragraph(f"{metrics.overall_score:.1f} / 10", big_score_style))
    story.append(Paragraph(metrics.grade, grade_style))
    story.append(Spacer(1, 3 * mm))

    # ── Score breakdown table ─────────────────────────────────────
    story.append(Paragraph("SCORE BREAKDOWN", section_style))

    breakdown_data = [
        ["Category", "Score", "Bar", "Details"],
        [
            "Golden Ratio (φ)",
            f"{metrics.golden_ratio_score:.1f}",
            _score_bar_text(metrics.golden_ratio_score),
            f"H/W ratio: {metrics.details.get('face_hw_ratio', 0):.3f} (ideal φ=1.618)",
        ],
        [
            "Facial Symmetry",
            f"{metrics.symmetry_score:.1f}",
            _score_bar_text(metrics.symmetry_score),
            f"Eye: {metrics.details.get('eye_symmetry', 0):.1f}  Cheek: {metrics.details.get('cheek_symmetry', 0):.1f}  Mouth: {metrics.details.get('mouth_symmetry', 0):.1f}",
        ],
        [
            "Facial Thirds",
            f"{metrics.facial_thirds_score:.1f}",
            _score_bar_text(metrics.facial_thirds_score),
            f"Upper: {metrics.details.get('upper_third_pct', 0):.1f}%  Mid: {metrics.details.get('middle_third_pct', 0):.1f}%  Lower: {metrics.details.get('lower_third_pct', 0):.1f}%",
        ],
        [
            "Canthal Tilt",
            f"{metrics.canthal_tilt_score:.1f}",
            _score_bar_text(metrics.canthal_tilt_score),
            f"Angle: {metrics.canthal_tilt_degrees:+.1f}° (ideal: +5° to +10°)",
        ],
        [
            "Jawline",
            f"{metrics.jaw_score:.1f}",
            _score_bar_text(metrics.jaw_score),
            f"Jaw/cheek ratio: {metrics.details.get('jaw_to_cheek_ratio', 0):.3f} (ideal ~0.75)",
        ],
    ]

    col_widths = [42 * mm, 18 * mm, 42 * mm, 58 * mm]

    def cell_style(row_idx, col_idx, value):
        if col_idx == 1 and row_idx > 0:
            try:
                s = float(value)
                c = _score_color(s)
            except Exception:
                c = TEXT_LIGHT
            return Paragraph(
                f'<font color="#{c.hexval()[1:]}" size="11"><b>{value}</b></font>',
                ParagraphStyle("cs", alignment=TA_CENTER, fontName="Helvetica-Bold"),
            )
        if col_idx == 2 and row_idx > 0:
            return Paragraph(
                f'<font face="Courier" size="7" color="#C9A84C">{value}</font>',
                ParagraphStyle("bar", alignment=TA_LEFT, fontName="Courier"),
            )
        if row_idx == 0:
            return Paragraph(
                f'<b>{value}</b>',
                ParagraphStyle("hdr", fontSize=9, textColor=ACCENT, fontName="Helvetica-Bold",
                               alignment=TA_CENTER if col_idx in (1, 2) else TA_LEFT),
            )
        return Paragraph(
            str(value),
            ParagraphStyle("cell", fontSize=9, textColor=TEXT_LIGHT, fontName="Helvetica",
                           leading=12),
        )

    table_data = [
        [cell_style(r, c, val) for c, val in enumerate(row)]
        for r, row in enumerate(breakdown_data)
    ]

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
            ("BACKGROUND", (0, 1), (-1, -1), PANEL_BG),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PANEL_BG, colors.HexColor("#141414")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#333333")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Measurements ─────────────────────────────────────────────
    story.append(Paragraph("FACIAL MEASUREMENTS", section_style))

    meas_data = [
        ["Measurement", "Value", "Measurement", "Value"],
        ["Face Width (px)", f"{metrics.face_width:.0f}", "Face Height (px)", f"{metrics.face_height:.0f}"],
        ["Left Eye Width", f"{metrics.left_eye_width:.1f}", "Right Eye Width", f"{metrics.right_eye_width:.1f}"],
        ["Nose Width", f"{metrics.nose_width:.1f}", "Mouth Width", f"{metrics.mouth_width:.1f}"],
        ["Interpupillary Dist.", f"{metrics.interpupillary_distance:.1f}", "IPD/Face ratio", f"{metrics.details.get('ipd_to_face_ratio', 0):.3f}"],
        ["Upper Third", f"{metrics.upper_third:.1f} px", "Upper Third %", f"{metrics.details.get('upper_third_pct', 0):.1f}%"],
        ["Middle Third", f"{metrics.middle_third:.1f} px", "Middle Third %", f"{metrics.details.get('middle_third_pct', 0):.1f}%"],
        ["Lower Third", f"{metrics.lower_third:.1f} px", "Lower Third %", f"{metrics.details.get('lower_third_pct', 0):.1f}%"],
    ]

    meas_tbl = Table(meas_data, colWidths=[50 * mm, 30 * mm, 50 * mm, 30 * mm])
    meas_tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PANEL_BG, colors.HexColor("#141414")]),
            ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_LIGHT),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#333333")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(meas_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Analysis & Advice ─────────────────────────────────────────
    story.append(Paragraph("ANALYSIS & LOOKSMAXXING ADVICE", section_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#333333"), spaceAfter=3 * mm))

    advice_items = _generate_advice(metrics)
    for title, text in advice_items:
        story.append(
            Paragraph(
                f'<font color="#C9A84C"><b>{title}</b></font> — {text}',
                body_style,
            )
        )

    # ── Grading scale ─────────────────────────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#333333"), spaceAfter=3 * mm))
    story.append(Paragraph("GRADING SCALE", section_style))

    scale_text = (
        "SSS (9.5+) Mythically Attractive  •  SS (9.0+) Exceptionally Attractive  •  "
        "S (8.5+) Highly Attractive  •  A+ (8.0+) Above Average  •  "
        "A (7.0+) Attractive  •  B (6.0+) Above Average  •  "
        "C (5.0+) Average  •  D (4.0+) Below Average  •  E (<4.0) Needs Improvement"
    )
    story.append(Paragraph(scale_text, dim_style))

    # ── Footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=2 * mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=TEXT_DIM, alignment=TA_CENTER, fontName="Helvetica",
    )
    story.append(
        Paragraph(
            "Generated by LooksMaxxing AI Bot  •  "
            "Analysis based on facial geometry and golden ratio principles  •  "
            "For entertainment purposes",
            footer_style,
        )
    )

    doc.build(story, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


def _generate_advice(m: FaceMetrics):
    items = []

    # Golden ratio
    if m.golden_ratio_score >= 8:
        items.append(("Golden Ratio", "Your face proportions are close to the divine golden ratio (φ=1.618). Maintain your current jaw and cheekbone structure."))
    elif m.golden_ratio_score >= 6:
        items.append(("Golden Ratio", "Your proportions are decent. Mewing (tongue posture) and chewing hard foods can improve jaw definition over time."))
    else:
        items.append(("Golden Ratio", "Your face proportions deviate from the golden ratio. Consider mewing, jaw exercises, and consulting an orthodontist for facial structure improvements."))

    # Symmetry
    if m.symmetry_score >= 8:
        items.append(("Symmetry", "Excellent facial symmetry — a strong indicator of genetic health and attractiveness. Maintain proper posture and sleep posture."))
    elif m.symmetry_score >= 6:
        items.append(("Symmetry", "Moderate symmetry. Unilateral chewing and sleeping on one side can worsen asymmetry. Try to chew on both sides equally and sleep on your back."))
    else:
        items.append(("Symmetry", "Notable asymmetry detected. This can be caused by posture, chewing habits, or sleeping position. Correct forward head posture and avoid chewing on one side."))

    # Facial thirds
    if m.facial_thirds_score >= 8:
        items.append(("Facial Thirds", "Your face is well-divided into equal thirds (hairline to brows, brows to nose base, nose to chin) — a classic hallmark of beauty."))
    else:
        lower_pct = m.details.get("lower_third_pct", 33)
        if lower_pct > 36:
            items.append(("Facial Thirds", "Your lower third appears elongated. Mewing can help shorten the lower third over time, and proper orthodontic treatment can address vertical excess."))
        elif lower_pct < 30:
            items.append(("Facial Thirds", "Your lower third is short. This can sometimes be addressed via chin implants or genioplasty for more facial balance."))
        else:
            items.append(("Facial Thirds", "Your facial thirds are slightly unbalanced. Focus on proper tongue posture (mewing) to improve mid-face and lower face proportions."))

    # Canthal tilt
    if m.canthal_tilt_degrees >= 5:
        items.append(("Canthal Tilt", f"Positive canthal tilt of {m.canthal_tilt_degrees:+.1f}° — 'hunter eyes' aesthetic, highly desirable. This is largely genetic but proper sleep and mewing can maintain it."))
    elif m.canthal_tilt_degrees >= 0:
        items.append(("Canthal Tilt", f"Neutral canthal tilt ({m.canthal_tilt_degrees:+.1f}°). Slightly positive is more attractive. Eye area exercises and reducing under-eye fat can improve the appearance."))
    else:
        items.append(("Canthal Tilt", f"Negative canthal tilt ({m.canthal_tilt_degrees:+.1f}°) — 'sad eyes' appearance. Blepharoplasty or canthoplasty are cosmetic options. Reducing eye puffiness can help."))

    # Jawline
    if m.jaw_score >= 8:
        items.append(("Jawline", "Strong, well-defined jawline with good jaw-to-cheek ratio. Maintain low body fat to keep jaw definition sharp."))
    elif m.jaw_score >= 6:
        items.append(("Jawline", "Moderate jaw definition. Lower body fat percentage, mewing, and chewing hard mastic gum can help define the jawline."))
    else:
        items.append(("Jawline", "Weak jaw definition detected. Focus on reducing body fat, consistent mewing, jaw exercises with mastic gum, and consider consulting a maxillofacial surgeon."))

    return items
