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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)
from telegram.constants import ParseMode

from face_analyzer import analyze_face
from pdf_generator import generate_brief_pdf, generate_full_pdf
from storage import (
    increment_daily_count, get_displayed_daily_count,
    save_admin_chat_id, get_admin_chat_id,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO, stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "face_landmarker.task")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

TRIBUTE_BRIEF_URL = "https://web.tribute.tg/p/w6R"
TRIBUTE_FULL_URL  = "https://web.tribute.tg/p/w6V"
SUPPORT_URL       = "https://t.me/facedex_support"
ADMIN_USERNAME    = "facedex_support"   # без @


# ════════════════════════════════════════════════════════════════════════════
#  Тексты
# ════════════════════════════════════════════════════════════════════════════

def _main_text() -> str:
    daily = get_displayed_daily_count()
    return (
        "✨ <b>Добро пожаловать в Facedex</b>\n\n"
        "🔬 Facedex математически измеряет, насколько гармонично черты твоего лица "
        "сочетаются друг с другом.\n\n"
        "<blockquote>"
        "💼 <b>Твой баланс:</b> 0 разборов\n"
        f"📊 <b>Сегодня пользователи провели разборов:</b> {daily}"
        "</blockquote>"
    )


ABOUT_TEXT = (
    "🔬 <b>Что такое Facedex?</b>\n\n"
    "Facedex — математический анализ гармонии лица на основе:\n\n"
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
    "➕ И ещё 6 метрик по нормам антропометриста Лесли Фаркаса.\n\n"
    "<i>Только для развлечения. Красота субъективна.</i>"
)

BRIEF_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа  ›  Оплата</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Краткий разбор\n\n"
    "💰 <b>Цена</b>  —  199 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "🔸 <b>Итоговая оценка гармонии:</b>\n"
    "математический балл по геометрии лица — насколько твои пропорции близки к норме.\n\n"
    "🔸 <b>Тир по looksmaxing-шкале:</b>\n"
    "LTN, MTN или HTN — твоя категория внешности.\n\n"
    "🔸 <b>Оценка по ключевым параметрам:</b>\n"
    "глаза, нос, губы, скулы, челюсть, брови, симметрия и баланс.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 <b>После оплаты:</b>\n\n"
    "Просто отправь фото в этот чат —\n"
    "бот автоматически начнёт разбор.\n\n"
    "Готовый PDF-отчёт получишь за <b>1 минуту</b> ⚡"
)

FULL_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа  ›  Оплата</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Полный разбор\n\n"
    "💰 <b>Цена</b>  —  499 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "🔹 <b>Персональный PDF-отчёт на 25 страниц:</b>\n"
    "полный анализ лица, итоговая оценка гармонии, диаграмма со всеми метриками.\n\n"
    "🔹 <b>Разбор 20 ключевых метрик лица:</b>\n"
    "пропорции сравниваются с нормативными значениями из исследования Лесли Фаркаса.\n\n"
    "🔹 <b>Наглядная визуализация измерений:</b>\n"
    "98 ключевых точек, все отрезки и соотношения.\n\n"
    "🔹 <b>Понятное объяснение каждой метрики:</b>\n"
    "что измеряется, какое значение и как влияет на гармонию.\n\n"
    "🔹 <b>Конкретные шаги по улучшению:</b>\n"
    "5 советов по слабым метрикам + 2 по уходу.\n\n"
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
        [InlineKeyboardButton("💬  Техподдержка", url=SUPPORT_URL),
         InlineKeyboardButton("❓  Что это?",     callback_data="about")],
    ])


def kb_plans():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋  Краткий разбор",  callback_data="plan_brief")],
        [InlineKeyboardButton("📊  Полный разбор",   callback_data="plan_full")],
        [InlineKeyboardButton("◀️  Назад",           callback_data="menu_main")],
    ])


def kb_brief():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой любой страны", url=TRIBUTE_BRIEF_URL)],
        [InlineKeyboardButton("◀️  Назад",           callback_data="menu_analyze"),
         InlineKeyboardButton("🏠  В главное меню",  callback_data="menu_main")],
    ])


def kb_full():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой любой страны", url=TRIBUTE_FULL_URL)],
        [InlineKeyboardButton("◀️  Назад",           callback_data="menu_analyze"),
         InlineKeyboardButton("🏠  В главное меню",  callback_data="menu_main")],
    ])


def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠  В главное меню", callback_data="menu_main")],
    ])


# ════════════════════════════════════════════════════════════════════════════
#  Хендлеры
# ════════════════════════════════════════════════════════════════════════════

def _is_admin(user) -> bool:
    return (user.username or "").lower() == ADMIN_USERNAME.lower()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Сохраняем chat_id администратора
    if _is_admin(user):
        save_admin_chat_id(update.effective_chat.id)
        logger.info(f"Admin chat_id saved: {update.effective_chat.id}")

    await update.message.reply_text(
        _main_text(), parse_mode=ParseMode.HTML, reply_markup=kb_main(),
    )
    await _send_example_pdfs(update.message.chat_id, context)


async def _send_example_pdfs(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    brief_path = os.path.join(ASSETS_DIR, "example_brief.pdf")
    full_path  = os.path.join(ASSETS_DIR, "example_full.pdf")
    if not (os.path.exists(brief_path) and os.path.exists(full_path)):
        return

    with open(brief_path, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id, document=f,
            filename="1. Краткий разбор лица — пример.pdf",
            caption="📋 <b>Краткий разбор</b> — пример отчёта (199 ₽)",
            parse_mode=ParseMode.HTML,
        )
    with open(full_path, "rb") as f:
        await context.bot.send_document(
            chat_id=chat_id, document=f,
            filename="2. Полный разбор лица — пример.pdf",
            caption="📊 <b>Полный разбор</b> — пример отчёта (499 ₽)",
            parse_mode=ParseMode.HTML,
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d = query.data

    if d == "menu_main":
        await query.edit_message_text(_main_text(), parse_mode=ParseMode.HTML,
                                      reply_markup=kb_main())
    elif d == "menu_analyze":
        await query.edit_message_text(
            "🔬 <b>Выбери формат разбора:</b>\n\n"
            "<blockquote>"
            "📋 <b>Краткий</b> — балл, тир, 8 параметров  (199 ₽)\n"
            "📊 <b>Полный</b> — 20 метрик, нормы Фаркаса, советы  (499 ₽)"
            "</blockquote>",
            parse_mode=ParseMode.HTML, reply_markup=kb_plans(),
        )
    elif d == "plan_brief":
        await query.edit_message_text(BRIEF_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_brief())
    elif d == "plan_full":
        await query.edit_message_text(FULL_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_full())
    elif d == "about":
        await query.edit_message_text(ABOUT_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_home())


# ── Анализ фото ──────────────────────────────────────────────────────────────

def _detect_face(img_bytes: bytes) -> bool:
    opts = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH), num_faces=1)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    rgb = cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with mp_vision.FaceLandmarker.create_from_options(opts) as det:
        return bool(det.detect(mp_img).face_landmarks)


async def _forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает сообщение/фото администратору."""
    admin_id = get_admin_chat_id()
    if not admin_id:
        return
    user = update.effective_user
    name = f"@{user.username}" if user.username else user.full_name
    try:
        await context.bot.send_message(
            admin_id,
            f"📩 <b>Сообщение от {name}</b> (id: <code>{user.id}</code>):",
            parse_mode=ParseMode.HTML,
        )
        await update.message.forward(admin_id)
    except Exception as e:
        logger.warning(f"Не удалось переслать: {e}")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Пересылаем фото администратору
    await _forward_to_admin(update, context)

    await update.message.reply_text("🔍 Определяю лицо...")

    tg_file  = await context.bot.get_file(update.message.photo[-1].file_id)
    img_bytes = bytes(await tg_file.download_as_bytearray())
    loop     = asyncio.get_event_loop()

    try:
        face_found = await loop.run_in_executor(None, _detect_face, img_bytes)
    except Exception as e:
        logger.warning(f"Предпроверка: {e}")
        face_found = True

    if not face_found:
        await update.message.reply_text(
            "❌ <b>Лицо не найдено!</b>\n\n"
            "Отправь чёткое фото анфас при хорошем освещении без тяжёлых фильтров.",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text(
        "✅ <b>Лицо найдено! Анализирую...</b>\n\nПодожди 15–30 секунд ⏳",
        parse_mode=ParseMode.HTML,
    )

    try:
        metrics = await loop.run_in_executor(None, analyze_face, img_bytes)
        if not metrics:
            await update.message.reply_text("❌ Анализ не удался. Попробуй другое фото.")
            return

        # Аннотированное фото
        if metrics.landmark_image:
            await context.bot.send_photo(
                update.effective_chat.id,
                photo=BytesIO(metrics.landmark_image),
                caption=(
                    f"🎯 <b>Общий балл: {metrics.overall_score}/10</b>\n"
                    f"🏆 {metrics.grade}\n"
                    f"🏷 {metrics.tier} — {_tier(metrics.tier)}\n\n"
                    f"📐 Золотое сечение: {metrics.golden_ratio_score}/10\n"
                    f"🪞 Симметрия: {metrics.symmetry_score}/10\n"
                    f"📏 Трети лица: {metrics.facial_thirds_score}/10\n"
                    f"👁 Кантальный тильт: {metrics.canthal_tilt_score}/10 ({metrics.canthal_tilt_degrees:+.1f}°)\n"
                    f"💪 Челюсть: {metrics.jaw_score}/10\n\n"
                    "<i>PDF-отчёт ниже 👇</i>"
                ),
                parse_mode=ParseMode.HTML,
            )

        username = user.username or user.first_name or "user"

        # Для администратора — отправляем оба PDF
        if _is_admin(user):
            brief_b = await loop.run_in_executor(None, generate_brief_pdf, metrics, username)
            await context.bot.send_document(
                update.effective_chat.id, BytesIO(brief_b),
                filename=f"facedex_brief_{user.id}.pdf",
                caption="📋 <b>Краткий разбор</b>",
                parse_mode=ParseMode.HTML,
            )

        pdf_b = await loop.run_in_executor(None, generate_full_pdf, metrics, username)
        await context.bot.send_document(
            update.effective_chat.id, BytesIO(pdf_b),
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
        logger.exception(f"Ошибка анализа {user.id}: {e}")
        await update.message.reply_text("❌ Что-то пошло не так. Попробуй ещё раз.")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает текстовые сообщения от пользователей администратору."""
    if _is_admin(update.effective_user):
        return   # своё сообщение не пересылаем себе
    await _forward_to_admin(update, context)


def _tier(t: str) -> str:
    return {"HTN": "High Tier Normie", "MTN": "Mid Tier Normie", "LTN": "Low Tier Normie"}.get(t, t)


# ════════════════════════════════════════════════════════════════════════════
#  Запуск
# ════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Facedex Bot запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
