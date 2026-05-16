import os
import sys
import logging
import asyncio
from io import BytesIO

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from face_analyzer import analyze_face
from pdf_generator import generate_pdf
from payments import ANALYSIS_PRICE_STARS, ANALYSIS_TITLE, ANALYSIS_DESCRIPTION, ANALYSIS_PAYLOAD
from storage import save_pending_photo, get_pending_photo, clear_pending_photo

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

WELCOME_TEXT = (
    "👁 *LooksMaxxing AI* — Facial Analysis Bot\n\n"
    "Send me a *clear, front-facing photo* of your face and I'll analyze:\n\n"
    "• 📐 Golden Ratio (φ) proportions\n"
    "• 🪞 Facial Symmetry\n"
    "• 📏 Facial Thirds balance\n"
    "• 👁 Canthal Tilt (hunter eyes score)\n"
    "• 💪 Jawline definition\n\n"
    "The full report with scores, measurements, and personalized looksmaxxing advice is delivered as a *PDF* for *50 Telegram Stars* ⭐\n\n"
    "📸 *Send your photo to begin!*"
)

HELP_TEXT = (
    "*How it works:*\n\n"
    "1. Send a front-facing photo (good lighting, neutral expression)\n"
    "2. Pay *50 Stars* ⭐ to generate the full report\n"
    "3. Receive an annotated photo + detailed PDF with:\n"
    "   — Overall attractiveness score (out of 10)\n"
    "   — Golden ratio analysis\n"
    "   — Symmetry breakdown\n"
    "   — Facial thirds balance\n"
    "   — Canthal tilt angle\n"
    "   — Jawline score\n"
    "   — Personalized improvement advice\n\n"
    "*Tips for best results:*\n"
    "• Use a well-lit photo\n"
    "• Face the camera directly (no angle)\n"
    "• Neutral expression\n"
    "• No heavy filters\n\n"
    "Commands: /start /help /about"
)

ABOUT_TEXT = (
    "*About LooksMaxxing AI*\n\n"
    "This bot uses computer vision and facial landmark detection to measure your facial geometry against "
    "classical beauty standards including:\n\n"
    "• *The Golden Ratio (φ = 1.618)* — The ratio found throughout nature and considered aesthetically ideal\n"
    "• *Facial Thirds* — Equal division of the face into upper, middle, and lower thirds\n"
    "• *Bilateral Symmetry* — Left/right facial balance\n"
    "• *Canthal Tilt* — The angle of the eye axis (positive = hunter eyes)\n"
    "• *Jaw Definition* — Jaw-to-cheekbone ratio\n\n"
    "_For entertainment and self-improvement awareness only. Beauty is subjective._"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 How it works", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])
    await update.message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT, parse_mode=ParseMode.MARKDOWN)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await query.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)
    elif query.data == "about":
        await query.message.reply_text(ABOUT_TEXT, parse_mode=ParseMode.MARKDOWN)
    elif query.data == "pay":
        user_id = query.from_user.id
        file_id = get_pending_photo(user_id)
        if not file_id:
            await query.message.reply_text(
                "⚠️ Your photo session expired. Please send your photo again."
            )
            return
        await _send_invoice(query.message, context, user_id)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    # Get the highest-resolution photo
    photo = message.photo[-1]
    file_id = photo.file_id

    # Save for after payment
    save_pending_photo(user.id, file_id)

    # Quick free preview: try to detect a face
    await message.reply_text("🔍 Detecting face...")
    try:
        tg_file = await context.bot.get_file(file_id)
        img_bytes = bytes(await tg_file.download_as_bytearray())

        import numpy as np
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        import os

        model_path = os.path.join(os.path.dirname(__file__), "..", "assets", "face_landmarker.task")
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1,
        )

        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        with mp_vision.FaceLandmarker.create_from_options(options) as detector:
            result = detector.detect(mp_image)

        if not result.face_landmarks:
            await message.reply_text(
                "❌ *No face detected!*\n\n"
                "Please send a clear, front-facing photo with good lighting and no heavy filters.",
                parse_mode=ParseMode.MARKDOWN,
            )
            clear_pending_photo(user.id)
            return

    except Exception as e:
        logger.warning(f"Face pre-check failed: {e}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ Pay {ANALYSIS_PRICE_STARS} Stars — Get Full Report", callback_data="pay")],
    ])

    await message.reply_text(
        "✅ *Face detected!*\n\n"
        f"Ready to generate your full analysis report.\n\n"
        f"Your report will include:\n"
        f"• Overall attractiveness score (out of 10)\n"
        f"• Golden Ratio, Symmetry, Facial Thirds\n"
        f"• Canthal Tilt angle & score\n"
        f"• Jawline rating\n"
        f"• Detailed measurements\n"
        f"• Personalized looksmaxxing advice\n\n"
        f"*Cost: {ANALYSIS_PRICE_STARS} Telegram Stars ⭐*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


async def _send_invoice(message, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    await context.bot.send_invoice(
        chat_id=message.chat_id,
        title=ANALYSIS_TITLE,
        description=ANALYSIS_DESCRIPTION,
        payload=ANALYSIS_PAYLOAD,
        currency="XTR",
        prices=[LabeledPrice(label="Full PDF Report", amount=ANALYSIS_PRICE_STARS)],
    )


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload != ANALYSIS_PAYLOAD:
        await query.answer(ok=False, error_message="Unknown payment payload.")
        return
    user_id = query.from_user.id
    if not get_pending_photo(user_id):
        await query.answer(
            ok=False,
            error_message="Your photo session expired. Please send your photo again."
        )
        return
    await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    await message.reply_text(
        "✅ *Payment received! Analyzing your face...*\n\n"
        "This may take 15–30 seconds. Please wait ⏳",
        parse_mode=ParseMode.MARKDOWN,
    )

    file_id = get_pending_photo(user.id)
    if not file_id:
        await message.reply_text(
            "⚠️ Sorry, your photo session expired. Please contact support — your Stars will be refunded."
        )
        return

    try:
        tg_file = await context.bot.get_file(file_id)
        img_bytes = bytes(await tg_file.download_as_bytearray())

        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, analyze_face, img_bytes)

        if metrics is None:
            await message.reply_text(
                "❌ Face analysis failed. Could not detect facial landmarks.\n"
                "Please try with a clearer front-facing photo."
            )
            clear_pending_photo(user.id)
            return

        # Generate annotated image
        if metrics.landmark_image:
            await context.bot.send_photo(
                chat_id=message.chat_id,
                photo=BytesIO(metrics.landmark_image),
                caption=(
                    f"🎯 *Overall Score: {metrics.overall_score}/10*\n"
                    f"🏆 Grade: {metrics.grade}\n\n"
                    f"📐 Golden Ratio: {metrics.golden_ratio_score}/10\n"
                    f"🪞 Symmetry: {metrics.symmetry_score}/10\n"
                    f"📏 Facial Thirds: {metrics.facial_thirds_score}/10\n"
                    f"👁 Canthal Tilt: {metrics.canthal_tilt_score}/10 ({metrics.canthal_tilt_degrees:+.1f}°)\n"
                    f"💪 Jawline: {metrics.jaw_score}/10\n\n"
                    "_Full PDF report below_ 👇"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

        # Generate PDF
        username = user.username or user.first_name or "User"
        pdf_bytes = await loop.run_in_executor(None, generate_pdf, metrics, username)

        await context.bot.send_document(
            chat_id=message.chat_id,
            document=BytesIO(pdf_bytes),
            filename=f"looksmaxxing_report_{user.id}.pdf",
            caption=(
                "📄 *Your Full Looksmaxxing Report*\n\n"
                "Includes all scores, detailed measurements, and personalized improvement advice.\n\n"
                "_Thank you for using LooksMaxxing AI!_ 🚀"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )

        clear_pending_photo(user.id)

    except Exception as e:
        logger.exception(f"Analysis failed for user {user.id}: {e}")
        await message.reply_text(
            "❌ Something went wrong during analysis. Please try again or contact support."
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    logger.info("LooksMaxxing AI Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
