"""
Generates a dark-themed instruction PDF with 8 rule images embedded.
One page per rule: title + image + description text.
"""
import os
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from instruction_images import (
    RULE_TITLES, RULE_DESCS, RULE_GENERATORS, generate_all_rule_images
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH  = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")

try:
    pdfmetrics.registerFont(TTFont("DV",  FONT_PATH))
    pdfmetrics.registerFont(TTFont("DVB", FONT_PATH))
except Exception:
    pass

PW, PH = A4  # 595 × 842 pt

# Dark palette
BG_HEX    = colors.HexColor("#0B0B12")
CARD_HEX  = colors.HexColor("#14141F")
GOLD_HEX  = colors.HexColor("#DAB428")
WHITE_HEX = colors.HexColor("#E8E8F5")
GREY_HEX  = colors.HexColor("#888899")
GREEN_HEX = colors.HexColor("#48D282")
RED_HEX   = colors.HexColor("#E64141")
LINE_HEX  = colors.HexColor("#282838")


def _c(y): return PH - y  # flip y (PDF origin is bottom-left)


def _draw_page_bg(c: pdfgen_canvas.Canvas):
    c.setFillColor(BG_HEX)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)


def _draw_cover(c: pdfgen_canvas.Canvas):
    _draw_page_bg(c)

    # Top accent bar
    c.setFillColor(GOLD_HEX)
    c.rect(0, PH - 8, PW, 8, fill=1, stroke=0)

    # Bot name
    c.setFont("DVB", 30)
    c.setFillColor(GOLD_HEX)
    title = "FACEDEX BOT"
    tw = c.stringWidth(title, "DVB", 30)
    c.drawString((PW - tw) / 2, _c(90), title)

    # Subtitle
    c.setFont("DV", 14)
    c.setFillColor(WHITE_HEX)
    sub = "Инструкция по съёмке"
    tw2 = c.stringWidth(sub, "DV", 14)
    c.drawString((PW - tw2) / 2, _c(120), sub)

    # Divider
    c.setStrokeColor(GOLD_HEX)
    c.setLineWidth(1)
    c.line(30 * mm, _c(135), PW - 30 * mm, _c(135))

    # Intro text
    intro_lines = [
        "Чтобы анализ был максимально точным — выполните",
        "все 8 правил из этой инструкции.",
        "",
        "Неправильное фото = неверные метрики.",
        "Правильное фото = точный разбор вашего лица.",
    ]
    c.setFont("DV", 13)
    c.setFillColor(GREY_HEX)
    y = 165
    for line in intro_lines:
        if line == "":
            y += 8
            continue
        tw3 = c.stringWidth(line, "DV", 13)
        c.drawString((PW - tw3) / 2, _c(y), line)
        y += 22

    # Rule list
    c.setFont("DV", 12)
    c.setFillColor(GREY_HEX)
    y += 20
    for i, t in enumerate(RULE_TITLES, 1):
        row = f"  {i:02d}.  {t}"
        color = GOLD_HEX if i % 2 == 0 else WHITE_HEX
        c.setFillColor(color)
        c.drawString(50 * mm, _c(y), row)
        y += 20

    # Bottom note
    c.setFont("DV", 10)
    c.setFillColor(GREY_HEX)
    note = "Все правила обязательны. Пропустить — значит получить неточный результат."
    tnw = c.stringWidth(note, "DV", 10)
    c.drawString((PW - tnw) / 2, _c(PH - 52), note)

    # Bottom accent
    c.setFillColor(GOLD_HEX)
    c.rect(0, 0, PW, 6, fill=1, stroke=0)


def _draw_rule_page(c: pdfgen_canvas.Canvas, num: int, img_path: str,
                    title: str, desc: tuple):
    _draw_page_bg(c)

    # Top accent bar
    c.setFillColor(GOLD_HEX)
    c.rect(0, PH - 6, PW, 6, fill=1, stroke=0)

    # Rule number badge
    badge_w = 38
    c.setFillColor(GOLD_HEX)
    c.roundRect(14 * mm, _c(52), badge_w, 28, 5, fill=1, stroke=0)
    c.setFont("DVB", 14)
    c.setFillColor(BG_HEX)
    num_str = f"{num:02d}"
    nw = c.stringWidth(num_str, "DVB", 14)
    c.drawString(14 * mm + (badge_w - nw) / 2, _c(44), num_str)

    # Rule title
    c.setFont("DVB", 18)
    c.setFillColor(WHITE_HEX)
    c.drawString(14 * mm + badge_w + 10, _c(48), title)

    # Thin gold divider
    c.setStrokeColor(GOLD_HEX)
    c.setLineWidth(0.6)
    c.line(14 * mm, _c(58), PW - 14 * mm, _c(58))

    # Rule image — full width
    img_y_top = 68  # from top
    img_h_pt  = int((PH - 68 - 95) * 0.86)   # leave room at bottom
    img_w_pt  = PW - 28 * mm

    if os.path.exists(img_path):
        pil = PILImage.open(img_path).convert("RGB")
        buf = BytesIO()
        pil.save(buf, "PNG")
        buf.seek(0)
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(buf)
        c.drawImage(ir,
                    14 * mm, _c(img_y_top + img_h_pt),
                    width=img_w_pt, height=img_h_pt,
                    preserveAspectRatio=True, anchor="c")

    # Description block
    desc_y = img_y_top + img_h_pt + 16
    c.setFillColor(CARD_HEX)
    c.roundRect(14 * mm, _c(desc_y + 44), PW - 28 * mm, 48, 6, fill=1, stroke=0)

    c.setFont("DV", 13)
    c.setFillColor(WHITE_HEX)
    for i, line in enumerate(desc):
        lw = c.stringWidth(line, "DV", 13)
        c.drawString(14 * mm + (PW - 28 * mm - lw) / 2,
                     _c(desc_y + 16 + i * 20), line)

    # Bottom accent
    c.setFillColor(LINE_HEX)
    c.rect(0, 0, PW, 5, fill=1, stroke=0)

    # Footer
    c.setFont("DV", 9)
    c.setFillColor(GREY_HEX)
    footer = f"Facedex Bot  ·  Правило {num} из 8"
    fw = c.stringWidth(footer, "DV", 9)
    c.drawString((PW - fw) / 2, 9, footer)


def generate_instruction_pdf(output_path: str = None) -> bytes:
    """
    Generate the instruction PDF with cover + 8 rule pages.
    Returns PDF bytes. If output_path given, also saves to file.
    """
    # Generate all 8 rule images first
    img_paths = generate_all_rule_images()

    buf = BytesIO()
    c = pdfgen_canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Инструкция по съёмке — Facedex Bot")
    c.setAuthor("Facedex Bot")

    # Cover page
    _draw_cover(c)
    c.showPage()

    # 8 rule pages
    for i, (title, desc, img_path) in enumerate(
            zip(RULE_TITLES, RULE_DESCS, img_paths), 1):
        _draw_rule_page(c, i, img_path, title, desc)
        c.showPage()

    c.save()
    pdf_bytes = buf.getvalue()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes


if __name__ == "__main__":
    out = os.path.join(ASSETS_DIR, "instruction.pdf")
    data = generate_instruction_pdf(out)
    print(f"Generated instruction PDF: {out}  ({len(data)//1024} KB)")
