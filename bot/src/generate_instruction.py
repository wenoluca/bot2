"""
Генерирует PDF-инструкцию по съёмке для Facedex.
Запускать из bot/src/:  python generate_instruction.py
"""
import io
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ASSETS   = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH = os.path.join(ASSETS, "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DV",  FONT_PATH))
pdfmetrics.registerFont(TTFont("DVB", FONT_PATH))

BG     = colors.HexColor("#0B0B0F")
PANEL  = colors.HexColor("#17171E")
PANEL2 = colors.HexColor("#111116")
GOLD   = colors.HexColor("#C9A84C")
GOLDB  = colors.HexColor("#E8C96A")
TEXT   = colors.HexColor("#EEEEF2")
DIM    = colors.HexColor("#6A6A80")
RED    = colors.HexColor("#F44336")
GREEN  = colors.HexColor("#4CAF50")
BORDER = colors.HexColor("#28283A")
ACCENT = colors.HexColor("#1E1E2C")
HEADER = colors.HexColor("#0D0D14")

W, H = A4
BODY = W - 36*mm
REGULAR, BOLD = "DV", "DVB"


def _s(name, **kw):
    from reportlab.lib.styles import ParagraphStyle
    d = dict(fontName=REGULAR, textColor=TEXT, fontSize=10, leading=14, spaceAfter=0)
    d.update(kw)
    return ParagraphStyle(name, **d)


def _dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, H - 3, W, 3, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 0, W, 2, fill=1, stroke=0)
    canvas.restoreState()


def _make_doc(path):
    return SimpleDocTemplate(path, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm)


def _rule_card(num, title, wrong_text, right_text, key_moment):
    num_cell = Table([[
        Paragraph(f"{num:02d}", _s("nc", fontName=BOLD, fontSize=22, textColor=GOLD,
                                   leading=26, alignment=TA_CENTER)),
    ]], colWidths=[16*mm])
    num_cell.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), HEADER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("BOX",          (0, 0), (-1, -1), 1, GOLD),
    ]))

    content_right = Table([[
        Paragraph(title, _s("rt", fontName=BOLD, fontSize=12, textColor=GOLDB, leading=16)),
    ], [
        Table([[
            Table([[
                Paragraph("✗ НЕПРАВИЛЬНО", _s("wh", fontName=BOLD, fontSize=8,
                                               textColor=RED, leading=11)),
                Paragraph(wrong_text, _s("wt", fontSize=9, textColor=TEXT, leading=13)),
            ]], colWidths=[None]),
            Table([[
                Paragraph("✓ ПРАВИЛЬНО", _s("rh", fontName=BOLD, fontSize=8,
                                             textColor=GREEN, leading=11)),
                Paragraph(right_text, _s("rt2", fontSize=9, textColor=TEXT, leading=13)),
            ]], colWidths=[None]),
        ]], colWidths=[(BODY - 20*mm) / 2, (BODY - 20*mm) / 2]),
    ], [
        Table([[
            Paragraph("КЛЮЧЕВОЙ МОМЕНТ", _s("km", fontName=BOLD, fontSize=8,
                                             textColor=GOLD, leading=11)),
            Paragraph(key_moment, _s("kmt", fontSize=9, textColor=TEXT, leading=13)),
        ]], colWidths=[None]),
    ]], colWidths=[None])
    content_right.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))

    card = Table([[num_cell, content_right]], colWidths=[20*mm, None])
    card.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), PANEL),
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("LINEAFTER",    (0, 0), (0, -1), 1.5, GOLD),
    ]))
    return KeepTogether([card, Spacer(1, 4*mm)])


def generate_instruction_pdf() -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    st = []

    # Шапка
    st.append(Paragraph("QZELS FACE BOT",
                         _s("t", fontName=BOLD, fontSize=30, textColor=GOLD,
                            alignment=TA_CENTER, spaceAfter=0)))
    st.append(Paragraph("Как сделать правильную фотографию для анализа",
                         _s("su", fontName=BOLD, fontSize=13, textColor=TEXT,
                            alignment=TA_CENTER, spaceAfter=1*mm)))
    st.append(Paragraph("8 правил для максимально точного результата",
                         _s("su2", fontSize=10, textColor=DIM, alignment=TA_CENTER,
                            spaceAfter=3*mm)))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=5*mm))

    # Почему это важно
    reasons = [
        "Поворот головы — искажает симметрию и ширину лица",
        "Положение подбородка — меняет вертикальные пропорции",
        "Волосы на лице — мешают определению ключевых точек",
        "Мимика — деформирует рот, щёки и нижнюю треть",
        "Освещение — скрывает контуры и создаёт ложные тени",
        "Качество снимка — снижает точность всего анализа",
        "Другие люди в кадре — нарушают детекцию лица",
        "Наклон головы — нарушает горизонтальную ось и все метрики",
    ]
    why_rows = [[
        Paragraph("ПОЧЕМУ ЭТО ВАЖНО",
                  _s("wh", fontName=BOLD, fontSize=10, textColor=GOLDB, leading=14)),
    ]]
    for r in reasons:
        why_rows.append([
            Paragraph(f"  ✦  {r}", _s("wr", fontSize=9, textColor=TEXT, leading=14)),
        ])
    why_tbl = Table(why_rows, colWidths=[BODY])
    why_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), HEADER),
        ("BACKGROUND",   (0, 1), (-1, -1), PANEL2),
        ("BOX",          (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    st.append(why_tbl)
    st.append(Spacer(1, 6*mm))

    # 8 правил
    rules = [
        (1, "Смотрите прямо в камеру",
         "Даже небольшой поворот головы влево или вправо.",
         "Анфас — лицо направлено строго прямо на камеру.",
         "Лицо должно смотреть строго прямо."),
        (2, "Не поднимайте и не опускайте подбородок",
         "Подбородок слегка поднят или опущен.",
         "Нейтральное положение головы — взгляд прямо перед собой.",
         "Держите голову естественно и ровно."),
        (3, "Лицо и лоб должны быть полностью открыты",
         "Волосы закрывают часть лба, уши или контур лица.",
         "Волосы убраны за уши, лоб и контур лица открыты.",
         "Уберите волосы назад и за уши."),
        (4, "Сохраняйте нейтральное выражение лица",
         "Заметная улыбка или активная мимика.",
         "Спокойное, безэмоциональное выражение.",
         "Фото должно быть как на паспорт: спокойно, без эмоций."),
        (5, "Используйте ровное освещение",
         "Тёмное, жёсткое или неравномерное освещение.",
         "Мягкий равномерный свет спереди, лицо хорошо видно.",
         "Лицо должно быть хорошо и равномерно освещено."),
        (6, "Фото должно быть чётким",
         "Размытый, нерезкий снимок.",
         "Резкое, хорошо сфокусированное фото.",
         "Используйте чёткое фото без смаза и расфокуса."),
        (7, "В кадре должен быть только один человек",
         "На фото присутствуют другие люди.",
         "В кадре только вы — никого рядом.",
         "Фотография должна содержать только одно лицо."),
        (8, "Не наклоняйте голову к плечу",
         "Голова наклонена к левому или правому плечу.",
         "Голова расположена ровно, без наклона в сторону.",
         "Голова должна быть ровной — без наклона к плечу."),
    ]
    for num, title, wrong, right, km in rules:
        st.append(_rule_card(num, title, wrong, right, km))

    # Чеклист
    st.append(Spacer(1, 2*mm))
    st.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3*mm))
    st.append(Paragraph("Чеклист перед съёмкой",
                         _s("clh", fontName=BOLD, fontSize=13, textColor=GOLDB,
                            spaceAfter=2*mm)))
    st.append(Paragraph("Убедитесь, что всё выполнено",
                         _s("cls", fontSize=9, textColor=DIM, spaceAfter=3*mm)))

    checklist = [
        "Смотрите прямо в камеру",
        "Держите голову ровно",
        "Не поднимайте и не опускайте подбородок",
        "Уберите волосы за уши, откройте лоб",
        "Сохраняйте нейтральное выражение лица",
        "Используйте хорошее равномерное освещение",
        "Делайте чёткое, сфокусированное фото",
        "В кадре должен быть только один человек",
        "Не наклоняйте голову к плечу",
    ]
    cl_rows = []
    for item in checklist:
        cl_rows.append([
            Paragraph("☐", _s("cb", fontName=BOLD, fontSize=11, textColor=GOLD,
                               leading=14, alignment=TA_CENTER)),
            Paragraph(item, _s("ci", fontSize=10, textColor=TEXT, leading=14)),
        ])
    cl_tbl = Table(cl_rows, colWidths=[10*mm, BODY - 10*mm])
    cl_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PANEL, PANEL2]),
        ("BOX",           (0, 0), (-1, -1), 0.6, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    st.append(cl_tbl)
    st.append(Spacer(1, 5*mm))

    # Призыв к действию
    cta_tbl = Table([[
        Table([[
            Paragraph("ГОТОВО?", _s("ctah", fontName=BOLD, fontSize=13, textColor=GOLDB, leading=16)),
            Paragraph("Отправьте фото в бот — и получите результат.",
                      _s("ctas", fontSize=10, textColor=TEXT, leading=14)),
            Paragraph("Анализ занимает около 30 секунд.",
                      _s("ctat", fontSize=9, textColor=DIM, leading=13)),
        ]], colWidths=[None]),
    ]], colWidths=[BODY])
    cta_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), ACCENT),
        ("BOX",          (0, 0), (-1, -1), 1.5, GOLD),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
    ]))
    st.append(cta_tbl)
    st.append(Spacer(1, 4*mm))
    st.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=2*mm))
    st.append(Paragraph("Qzels Face Bot  •  Математический анализ гармонии лица",
                         _s("ft", fontSize=8, textColor=DIM, alignment=TA_CENTER)))

    doc.build(st, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()


if __name__ == "__main__":
    out_path = os.path.join(ASSETS, "instruction.pdf")
    print("Генерирую PDF-инструкцию...")
    with open(out_path, "wb") as f:
        f.write(generate_instruction_pdf())
    print(f"  ✓ {out_path}")
    print("Готово!")
