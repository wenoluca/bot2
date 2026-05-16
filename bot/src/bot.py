import os
import sys
import logging
import asyncio
from io import BytesIO

import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from face_analyzer import analyze_face
from pdf_generator import generate_brief_pdf, generate_full_pdf
from storage import increment_daily_count, get_displayed_daily_count

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL_PATH  = os.path.join(os.path.dirname(__file__), "..", "assets", "face_landmarker.task")
ASSETS_DIR  = os.path.join(os.path.dirname(__file__), "..", "assets")

# ── Ссылки Tribute (замените на свои после создания продуктов в @TributeAppBot) ──
TRIBUTE_BRIEF_URL = "https://t.me/tribute"   # замените на ссылку продукта 199 ₽
TRIBUTE_FULL_URL  = "https://t.me/tribute"   # замените на ссылку продукта 499 ₽

SUPPORT_URL = "https://t.me/facedex_support" # замените на свой аккаунт поддержки


# ════════════════════════════════════════════════════════════════════════════
#  Тексты
# ════════════════════════════════════════════════════════════════════════════

def _main_menu_text() -> str:
    daily = get_displayed_daily_count()
    return (
        "✨ <b>Добро пожаловать в Facedex</b>\n\n"
        "🔬 Facedex математически измеряет, насколько гармонично черты твоего лица сочетаются друг с другом.\n\n"
        "<blockquote>"
        "💼 <b>Твой баланс:</b> 0 разборов\n"
        f"📊 <b>Сегодня пользователи провели разборов:</b> {daily}"
        "</blockquote>"
    )


ABOUT_TEXT = (
    "🔬 <b>Что такое Facedex?</b>\n\n"
    "Facedex — это математический анализ гармонии лица на основе:\n\n"
    "📐 <b>Золотого сечения (φ = 1.618)</b>\n"
    "Идеальная пропорция, встречающаяся в природе и классической красоте.\n\n"
    "🪞 <b>Симметрии лица</b>\n"
    "Сравнение левой и правой половин по ключевым точкам.\n\n"
    "📏 <b>Трёх третей лица</b>\n"
    "Лоб, нос и подбородок должны быть равными третями.\n\n"
    "👁 <b>Кантального тильта</b>\n"
    "Угол наклона глазной оси (+5°…+10° — «охотничьи глаза»).\n\n"
    "💪 <b>Линии челюсти</b>\n"
    "Соотношение ширины челюсти к скулам.\n\n"
    "➕ И другие метрики по нормам антропометриста Лесли Фаркаса.\n\n"
    "<i>Только для развлечения. Красота субъективна.</i>"
)

SUPPORT_TEXT = (
    "💬 <b>Техподдержка Facedex</b>\n\n"
    "Если у вас возникли вопросы или проблемы — напишите нам:\n\n"
    "👉 @facedex_support\n\n"
    "<i>Обычно отвечаем в течение нескольких часов.</i>"
)

BRIEF_PLAN_TEXT = (
    "📍 <b>Главное меню › Выбор тарифа › Оплата</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "⚜️ <b>План</b>  —  Краткий разбор\n\n"
    "💰 <b>Цена</b>  —  199 ₽\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "🔸 <b>Итоговая оценка гармонии:</b>\n"
    "математический балл по геометрии лица — насколько твои пропорции близки к норме.\n\n"
    "🔸 <b>Тир по looksmaxing-шкале:</b>\n"
    "LTN, MTN или HTN — твоя категория внешности.\n\n"
    "🔸 <b>Оценка по ключевым параметрам:</b>\n"
    "глаза, нос, губы, скулы, челюсть, брови, симметрия и баланс — "
    "где у тебя сильные стороны и где оценка проседает.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 <b>После оплаты:</b>\n\n"
    "Просто отправь фото в этот чат —\n"
    "бот автоматически начнёт разбор.\n\n"
    "Готовый PDF-отчёт получишь за <b>1 минуту</b> ⚡"
)

FULL_PLAN_TEXT = (
    "📍 <b>Главное меню › Выбор тарифа › Оплата</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "⚜️ <b>План</b>  —  Полный разбор\n\n"
    "💰 <b>Цена</b>  —  499 ₽\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "🔹 <b>Персональный PDF-отчёт на 25 страниц:</b>\n"
    "полный анализ лица; итоговая оценка гармонии, диаграмма со всеми метриками и визуализация пропорций.\n\n"
    "🔹 <b>Разбор 20 ключевых метрик лица:</b>\n"
    "пропорции твоего лица сравниваются с нормативными значениями из исследования лицевой антропометрии Лесли Фаркаса.\n\n"
    "🔹 <b>Наглядная визуализация измерений:</b>\n"
    "на твоё лицо накладываются 98 ключевых точек, все отрезки и соотношения, по которым считаются пропорции.\n\n"
    "🔹 <b>Понятное объяснение каждой метрики:</b>\n"
    "что именно измеряется, какое значение получилось и как этот показатель влияет на гармонию твоего лица.\n\n"
    "🔹 <b>Конкретные шаги по улучшению:</b>\n"
    "5 советов по самым слабым метрикам и 2 — по уходу; мы расскажем, что менять в первую очередь и что даст максимальный эффект.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 <b>После оплаты:</b>\n\n"
    "Просто отправь фото в этот чат —\n"
    "бот автоматически начнёт разбор.\n\n"
    "Готовый PDF-отчёт получишь за <b>2 минуты</b> ⚡"
)


# ════════════════════════════════════════════════════════════════════════════
#  Клавиатуры
# ════════════════════════════════════════════════════════════════════════════

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔬  Получить разбор лица", callback_data="menu_analyze")],
        [
            InlineKeyboardButton("💬 Техподдержка",  url=SUPPORT_URL),
            InlineKeyboardButton("❓ Что это?",       callback_data="about"),
        ],
    ])


def kb_plans():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋  Краткий разбор",  callback_data="plan_brief")],
        [InlineKeyboardButton("📊  Полный разбор",   callback_data="plan_full")],
        [InlineKeyboardButton("◀️  Назад",           callback_data="menu_main")],
    ])


def kb_brief_payment():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой любой страны", url=TRIBUTE_BRIEF_URL)],
        [
            InlineKeyboardButton("◀️ Назад",          callback_data="menu_analyze"),
            InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main"),
        ],
    ])


def kb_full_payment():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой любой страны", url=TRIBUTE_FULL_URL)],
        [
            InlineKeyboardButton("◀️ Назад",          callback_data="menu_analyze"),
            InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main"),
        ],
    ])


# ════════════════════════════════════════════════════════════════════════════
#  Хендлеры
# ════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        _main_menu_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=kb_main(),
    )
    # Отправляем примеры PDF отдельным сообщением
    await _send_example_pdfs(update.message.chat_id, context)


async def _send_example_pdfs(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    brief_path = os.path.join(ASSETS_DIR, "example_brief.pdf")
    full_path  = os.path.join(ASSETS_DIR, "example_full.pdf")

    if not (os.path.exists(brief_path) and os.path.exists(full_path)):
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📂 <b>Примеры отчётов Facedex</b>\n\n"
            "Ниже — два PDF-примера на основе искусственно созданного привлекательного мужского лица:"
        ),
        parse_mode=ParseMode.HTML,
    )

    with open(brief_path, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id,
            document=f,
            filename="1. Краткий разбор лица — пример.pdf",
            caption="📋 <b>Краткий разбор</b> — пример отчёта (199 ₽)",
            parse_mode=ParseMode.HTML,
        )

    with open(full_path, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id,
            document=f,
            filename="2. Полный разбор лица — пример.pdf",
            caption="📊 <b>Полный разбор</b> — пример отчёта (499 ₽)",
            parse_mode=ParseMode.HTML,
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_main":
        await query.edit_message_text(
            _main_menu_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_main(),
        )

    elif data == "menu_analyze":
        await query.edit_message_text(
            "🔬 <b>Выбери формат разбора:</b>\n\n"
            "<blockquote>"
            "📋 <b>Краткий</b> — балл, тир, 8 параметров (199 ₽)\n"
            "📊 <b>Полный</b> — 20 метрик, нормы Фаркаса, советы (499 ₽)"
            "</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_plans(),
        )

    elif data == "plan_brief":
        await query.edit_message_text(
            BRIEF_PLAN_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=kb_brief_payment(),
        )

    elif data == "plan_full":
        await query.edit_message_text(
            FULL_PLAN_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=kb_full_payment(),
        )

    elif data == "about":
        await query.edit_message_text(
            ABOUT_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 В главное меню", callback_data="menu_main")],
            ]),
        )


# ── Анализ фото ──────────────────────────────────────────────────────────────

def _detect_face(img_bytes: bytes) -> bool:
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img_cv = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with mp_vision.FaceLandmarker.create_from_options(options) as det:
        res = det.detect(mp_img)
    return bool(res.face_landmarks)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    photo = message.photo[-1]
    await message.reply_text("🔍 Определяю лицо...")

    tg_file = await context.bot.get_file(photo.file_id)
    img_bytes = bytes(await tg_file.download_as_bytearray())

    loop = asyncio.get_event_loop()

    try:
        face_found = await loop.run_in_executor(None, _detect_face, img_bytes)
    except Exception as e:
        logger.warning(f"Предпроверка лица: {e}")
        face_found = True

    if not face_found:
        await message.reply_text(
            "❌ <b>Лицо не найдено!</b>\n\n"
            "Пожалуйста, отправь чёткое фото анфас при хорошем освещении без тяжёлых фильтров.",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.reply_text(
        "✅ <b>Лицо найдено! Анализирую...</b>\n\n"
        "Запускаю полный геометрический анализ. Подожди 15–30 секунд ⏳",
        parse_mode=ParseMode.HTML,
    )

    try:
        metrics = await loop.run_in_executor(None, analyze_face, img_bytes)

        if metrics is None:
            await message.reply_text(
                "❌ Анализ не удался — не удалось определить ключевые точки лица.\n"
                "Попробуй другое фото: анфас, хорошее освещение."
            )
            return

        # Аннотированное фото с баллом
        if metrics.landmark_image:
            await context.bot.send_photo(
                chat_id=message.chat_id,
                photo=BytesIO(metrics.landmark_image),
                caption=(
                    f"🎯 <b>Общий балл: {metrics.overall_score}/10</b>\n"
                    f"🏆 Грейд: {metrics.grade}\n"
                    f"🏷 Тир: {metrics.tier} — {_tier_desc(metrics.tier)}\n\n"
                    f"📐 Золотое сечение: {metrics.golden_ratio_score}/10\n"
                    f"🪞 Симметрия: {metrics.symmetry_score}/10\n"
                    f"📏 Трети лица: {metrics.facial_thirds_score}/10\n"
                    f"👁 Кантальный тильт: {metrics.canthal_tilt_score}/10 "
                    f"({metrics.canthal_tilt_degrees:+.1f}°)\n"
                    f"💪 Челюсть: {metrics.jaw_score}/10\n\n"
                    "<i>Полный PDF-отчёт ниже 👇</i>"
                ),
                parse_mode=ParseMode.HTML,
            )

        username = user.username or user.first_name or "user"

        # Полный PDF
        pdf_bytes = await loop.run_in_executor(None, generate_full_pdf, metrics, username)
        await context.bot.send_document(
            chat_id=message.chat_id,
            document=BytesIO(pdf_bytes),
            filename=f"facedex_full_{user.id}.pdf",
            caption=(
                "📊 <b>Полный разбор Facedex</b>\n\n"
                "Все баллы, измерения, нормы Фаркаса и персональные советы.\n\n"
                "<i>Спасибо, что используешь Facedex!</i> 🚀"
            ),
            parse_mode=ParseMode.HTML,
        )

        increment_daily_count()

    except Exception as e:
        logger.exception(f"Ошибка анализа для {user.id}: {e}")
        await message.reply_text("❌ Что-то пошло не так. Попробуй ещё раз.")


def _tier_desc(tier: str) -> str:
    return {
        "HTN": "High Tier Normie",
        "MTN": "Mid Tier Normie",
        "LTN": "Low Tier Normie",
    }.get(tier, tier)


# ════════════════════════════════════════════════════════════════════════════
#  Запуск
# ════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    logger.info("Facedex Bot запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
