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
    grant_analysis, consume_grant, get_grant,
    register_user, get_all_user_ids,
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
ADMIN_USERNAME    = "facedex_support"


# ════════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════════

def _is_admin(user) -> bool:
    return (user.username or "").lower() == ADMIN_USERNAME.lower()


def _tier_label(t):
    return {"HTN":"High Tier Normie","MTN":"Mid Tier Normie","LTN":"Low Tier Normie"}.get(t, t)


# ════════════════════════════════════════════════════════════════════════════
#  Тексты / клавиатуры
# ════════════════════════════════════════════════════════════════════════════

def _main_text() -> str:
    daily = get_displayed_daily_count()
    return (
        "✨ <b>Добро пожаловать в Facedex</b>\n\n"
        "🔬 Facedex математически измеряет, насколько гармонично черты твоего лица "
        "сочетаются друг с другом.\n\n"
        "<blockquote>"
        "💼 <b>Твой баланс:</b> 0 разборов\n"
        f"📊 <b>Сегодня пользователи сделали разборов:</b> {daily}"
        "</blockquote>"
    )


ABOUT_TEXT = (
    "🔬 <b>Что такое Facedex?</b>\n\n"
    "Facedex — математический анализ гармонии лица:\n\n"
    "📐 <b>Золотое сечение φ = 1.618</b> — идеальные пропорции\n"
    "🪞 <b>Симметрия</b> — сравнение левой и правой половин\n"
    "📏 <b>Три трети лица</b> — лоб, нос и подбородок\n"
    "👁 <b>Кантальный тильт</b> — угол глазной оси\n"
    "💪 <b>Линия челюсти</b> — соотношение челюсти и скул\n"
    "➕ И ещё 6 метрик по нормам Лесли Фаркаса\n\n"
    "<i>Только для развлечения. Красота субъективна.</i>"
)

BRIEF_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Краткий разбор\n\n"
    "💰 <b>Цена</b>  —  199 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит:</b>\n"
    "🔸 Итоговый балл и тир (LTN / MTN / HTN)\n"
    "🔸 8 ключевых параметров лица\n"
    "🔸 Аннотированное фото с разметкой\n"
    "🔸 PDF-отчёт со шкалой оценок\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 После оплаты свяжитесь с @facedex_support, "
    "чтобы получить разбор. Готовый PDF за <b>1 мин</b> ⚡"
)

FULL_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Полный разбор\n\n"
    "💰 <b>Цена</b>  —  499 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит:</b>\n"
    "🔹 11 метрик по нормам Лесли Фаркаса\n"
    "🔹 Таблица измерений с идеальными значениями\n"
    "🔹 Аннотированное фото с разметкой 98 точек\n"
    "🔹 Персональные советы: причёска, уход, мьюинг\n"
    "🔹 Полный PDF-отчёт\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 После оплаты свяжитесь с @facedex_support, "
    "чтобы получить разбор. Готовый PDF за <b>2 мин</b> ⚡"
)

WAITING_TEXT = (
    "📩 <b>Фото получено!</b>\n\n"
    "Отправьте фото после того как свяжетесь с поддержкой (@facedex_support) "
    "и получите разрешение. Разбор будет выполнен вручную — это гарантирует качество.\n\n"
    "После оплаты: просто напишите @facedex_support и вам активируют разбор 🚀"
)


def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔬  Получить разбор лица", callback_data="menu_analyze")],
        [InlineKeyboardButton("💬  Техподдержка", url=SUPPORT_URL),
         InlineKeyboardButton("❓  Что это?",     callback_data="about")],
    ])

def kb_plans():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋  Краткий разбор  —  199 ₽", callback_data="plan_brief")],
        [InlineKeyboardButton("📊  Полный разбор  —  499 ₽",  callback_data="plan_full")],
        [InlineKeyboardButton("◀️  Назад",                     callback_data="menu_main")],
    ])

def kb_brief():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой", url=TRIBUTE_BRIEF_URL)],
        [InlineKeyboardButton("◀️  Назад",          callback_data="menu_analyze"),
         InlineKeyboardButton("🏠  Главное меню",   callback_data="menu_main")],
    ])

def kb_full():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳  Оплатить картой", url=TRIBUTE_FULL_URL)],
        [InlineKeyboardButton("◀️  Назад",           callback_data="menu_analyze"),
         InlineKeyboardButton("🏠  Главное меню",    callback_data="menu_main")],
    ])

def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠  Главное меню", callback_data="menu_main")],
    ])


# ════════════════════════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(update.effective_chat.id)
    if _is_admin(user):
        save_admin_chat_id(update.effective_chat.id)
        logger.info(f"Admin chat_id: {update.effective_chat.id}")

    await update.message.reply_text(
        _main_text(), parse_mode=ParseMode.HTML, reply_markup=kb_main())
    await _send_example_pdfs(update.effective_chat.id, context)


async def _send_example_pdfs(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    for fname, caption in [
        ("example_brief.pdf", "📋 <b>Краткий разбор</b> — пример отчёта (199 ₽)"),
        ("example_full.pdf",  "📊 <b>Полный разбор</b> — пример отчёта (499 ₽)"),
    ]:
        path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(path):
            with open(path, "rb") as f:
                await context.bot.send_document(
                    chat_id, document=f,
                    filename=fname.replace("_", " ").replace(".pdf", " — пример.pdf"),
                    caption=caption, parse_mode=ParseMode.HTML)


# ════════════════════════════════════════════════════════════════════════════
#  Callback кнопок
# ════════════════════════════════════════════════════════════════════════════

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
            "📋 <b>Краткий</b> — балл, тир, 8 параметров\n"
            "📊 <b>Полный</b> — 11 метрик, нормы Фаркаса, советы"
            "</blockquote>",
            parse_mode=ParseMode.HTML, reply_markup=kb_plans())
    elif d == "plan_brief":
        await query.edit_message_text(BRIEF_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_brief())
    elif d == "plan_full":
        await query.edit_message_text(FULL_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_full())
    elif d == "about":
        await query.edit_message_text(ABOUT_TEXT, parse_mode=ParseMode.HTML,
                                      reply_markup=kb_home())


# ════════════════════════════════════════════════════════════════════════════
#  Админ-команды
# ════════════════════════════════════════════════════════════════════════════

async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /grant @username brief|full
    Выдать пользователю один бесплатный разбор.
    """
    user = update.effective_user
    if not _is_admin(user):
        await update.message.reply_text("⛔ Эта команда только для администратора.")
        return

    args = context.args  # list of strings after /grant
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /grant @username brief|full\n\n"
            "Пример: /grant @ivan_petrov full")
        return

    username = args[0].lstrip("@").lower()
    tier = args[1].lower()
    if tier not in ("brief", "full"):
        await update.message.reply_text("Тип разбора: brief или full")
        return

    grant_analysis(username, tier)
    tier_ru = "Краткий" if tier == "brief" else "Полный"
    await update.message.reply_text(
        f"✅ Пользователю @{username} выдан <b>{tier_ru} разбор</b>.\n\n"
        f"Пусть отправит фото анфас в этот бот.",
        parse_mode=ParseMode.HTML)

    # Уведомить пользователя если знаем его chat_id — пока пропустим
    # (они сами напишут в бот и получат)


async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /announce <текст>
    Отправить сообщение всем пользователям бота.
    """
    user = update.effective_user
    if not _is_admin(user):
        await update.message.reply_text("⛔ Эта команда только для администратора.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /announce <ваш текст>")
        return

    text = " ".join(context.args)
    msg = (
        "📢 <b>Сообщение от Facedex:</b>\n\n"
        f"{text}"
    )
    ids = get_all_user_ids()
    sent, failed = 0, 0
    for cid in ids:
        try:
            await context.bot.send_message(cid, msg, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"📤 Рассылка завершена.\n✅ Доставлено: {sent}\n❌ Ошибок: {failed}")


# ════════════════════════════════════════════════════════════════════════════
#  Анализ фото
# ════════════════════════════════════════════════════════════════════════════

def _detect_face(img_bytes: bytes) -> bool:
    opts = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH), num_faces=1)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    rgb = cv2.cvtColor(cv2.imdecode(arr, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with mp_vision.FaceLandmarker.create_from_options(opts) as det:
        return bool(det.detect(mp_img).face_landmarks)


async def _forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = get_admin_chat_id()
    if not admin_id:
        return
    user = update.effective_user
    name = f"@{user.username}" if user.username else user.full_name
    try:
        await context.bot.send_message(
            admin_id,
            f"📩 <b>{name}</b> (id: <code>{user.id}</code>):",
            parse_mode=ParseMode.HTML)
        await update.message.forward(admin_id)
    except Exception as e:
        logger.warning(f"Forward error: {e}")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = (user.username or "").lower()

    # Всегда пересылаем фото администратору
    await _forward_to_admin(update, context)

    # Проверяем грант (или это сам админ)
    tier = None
    if _is_admin(user):
        tier = "full"
    else:
        tier = consume_grant(username)

    if not tier:
        # Нет гранта — сообщаем об оплате
        await update.message.reply_text(
            "🔒 <b>Сначала оплатите разбор</b>\n\n"
            "После оплаты свяжитесь с @facedex_support — "
            "мы активируем ваш разбор вручную.\n\n"
            "Выберите тариф в главном меню:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_plans())
        return

    await update.message.reply_text("🔍 Определяю лицо...")

    tg_file   = await context.bot.get_file(update.message.photo[-1].file_id)
    img_bytes = bytes(await tg_file.download_as_bytearray())
    loop      = asyncio.get_event_loop()

    try:
        face_found = await loop.run_in_executor(None, _detect_face, img_bytes)
    except Exception as e:
        logger.warning(f"Face pre-check: {e}")
        face_found = True

    if not face_found:
        # Возвращаем грант — пусть повторит с другим фото
        if not _is_admin(user):
            grant_analysis(username, tier)
        await update.message.reply_text(
            "❌ <b>Лицо не найдено!</b>\n\n"
            "Отправь чёткое фото анфас при хорошем освещении.",
            parse_mode=ParseMode.HTML)
        return

    await update.message.reply_text(
        "✅ <b>Лицо найдено! Анализирую...</b>\n\nПодожди 15–30 секунд ⏳",
        parse_mode=ParseMode.HTML)

    try:
        metrics = await loop.run_in_executor(None, analyze_face, img_bytes)
        if not metrics:
            if not _is_admin(user):
                grant_analysis(username, tier)  # возвращаем грант
            await update.message.reply_text("❌ Анализ не удался. Попробуй другое фото.")
            return

        # Аннотированное фото
        if metrics.landmark_image:
            await context.bot.send_photo(
                update.effective_chat.id,
                photo=BytesIO(metrics.landmark_image),
                caption=(
                    f"🎯 <b>Итоговый балл: {metrics.overall_score}/10</b>\n"
                    f"🏆 {metrics.grade}\n"
                    f"🏷 {metrics.tier} — {_tier_label(metrics.tier)}\n\n"
                    f"📐 Золотое сечение: {metrics.golden_ratio_score}/10\n"
                    f"🪞 Симметрия: {metrics.symmetry_score}/10\n"
                    f"📏 Трети лица: {metrics.facial_thirds_score}/10\n"
                    f"👁 Кантальный тильт: {metrics.canthal_tilt_score}/10 "
                    f"({metrics.canthal_tilt_degrees:+.1f}°)\n"
                    f"💪 Челюсть: {metrics.jaw_score}/10\n\n"
                    "<i>PDF-отчёт ниже 👇</i>"
                ),
                parse_mode=ParseMode.HTML)

        uname = user.username or user.first_name or "user"

        # Краткий — если тариф brief
        if tier == "brief":
            pdf_b = await loop.run_in_executor(None, generate_brief_pdf, metrics, uname)
            await context.bot.send_document(
                update.effective_chat.id, BytesIO(pdf_b),
                filename=f"facedex_brief_{user.id}.pdf",
                caption="📋 <b>Краткий разбор Facedex</b>\n\nСпасибо, что используешь Facedex! 🚀",
                parse_mode=ParseMode.HTML)
        else:
            # full — или для admin отправляем оба
            if _is_admin(user):
                pdf_b = await loop.run_in_executor(None, generate_brief_pdf, metrics, uname)
                await context.bot.send_document(
                    update.effective_chat.id, BytesIO(pdf_b),
                    filename=f"facedex_brief_{user.id}.pdf",
                    caption="📋 <b>Краткий разбор</b> (администратор — превью)",
                    parse_mode=ParseMode.HTML)

            pdf_f = await loop.run_in_executor(None, generate_full_pdf, metrics, uname)
            await context.bot.send_document(
                update.effective_chat.id, BytesIO(pdf_f),
                filename=f"facedex_full_{user.id}.pdf",
                caption=(
                    "📊 <b>Полный разбор Facedex</b>\n\n"
                    "Баллы, измерения, сравнение с нормами Фаркаса и персональные советы.\n\n"
                    "<i>Спасибо, что используешь Facedex!</i> 🚀"
                ),
                parse_mode=ParseMode.HTML)

        increment_daily_count()

    except Exception as e:
        logger.exception(f"Analysis error {user.id}: {e}")
        if not _is_admin(user):
            grant_analysis(username, tier)  # возвращаем грант при ошибке
        await update.message.reply_text("❌ Что-то пошло не так. Попробуй ещё раз.")


# ════════════════════════════════════════════════════════════════════════════
#  Текстовые сообщения
# ════════════════════════════════════════════════════════════════════════════

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_admin(update.effective_user):
        return  # свои сообщения не пересылаем
    register_user(update.effective_chat.id)
    await _forward_to_admin(update, context)


# ════════════════════════════════════════════════════════════════════════════
#  Запуск
# ════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("grant",    cmd_grant))
    app.add_handler(CommandHandler("announce", cmd_announce))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Facedex Bot запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
