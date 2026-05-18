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
    save_user_chat_id, get_chat_id_by_username,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO, stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "face_landmarker.task")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

TRIBUTE_BRIEF_URL = "https://t.me/tribute/app?startapp=dKmE"
TRIBUTE_FULL_URL  = "https://t.me/tribute/app?startapp=dKmF"
SUPPORT_URL       = "https://t.me/facedex_support"
ADMIN_USERNAME    = "facedex_support"


# ════════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════════

def _is_admin(user) -> bool:
    return (user.username or "").lower() == ADMIN_USERNAME.lower()


def _tier_label(t):
    return {
        "True Adam": "True Adam",
        "Chad":      "Chad",
        "Chadlite":  "Chadlite",
        "HTN":       "High Tier Normie",
        "MTN":       "Mid Tier Normie",
        "LTN":       "Low Tier Normie",
    }.get(t, t)


# ════════════════════════════════════════════════════════════════════════════
#  Тексты / клавиатуры
# ════════════════════════════════════════════════════════════════════════════

def _main_text() -> str:
    daily = get_displayed_daily_count()
    return (
        "✨ <b>Добро пожаловать в Qzels Face Bot</b>\n\n"
        "🔬 Qzels Face Bot математически измеряет, насколько гармонично черты твоего лица "
        "сочетаются друг с другом.\n\n"
        "<blockquote>"
        "💼 <b>Твой баланс:</b> 0 разборов\n"
        f"📊 <b>Сегодня пользователи сделали разборов:</b> {daily}"
        "</blockquote>\n\n"
        "<i>Бот разработан @facedex_support</i>"
    )


ABOUT_TEXT = (
    "🔬 <b>Что такое Qzels Face Bot?</b>\n\n"
    "Qzels Face Bot — математический анализ гармонии лица:\n\n"
    "📐 <b>Золотое сечение φ = 1.618</b> — идеальные пропорции\n"
    "🪞 <b>Симметрия</b> — сравнение левой и правой половин\n"
    "📏 <b>Три трети лица</b> — лоб, нос и подбородок\n"
    "👁 <b>Кантальный тильт</b> — угол глазной оси\n"
    "💪 <b>Линия челюсти</b> — соотношение челюсти и скул\n"
    "➕ И ещё 15 метрик по нормам Лесли Фаркаса\n\n"
    "<i>Только для развлечения. Красота субъективна.</i>"
)

ANALYZE_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа</b>\n\n"
    "<blockquote>"
    "🔬 После разбора ты поймёшь:\n\n"
    "— какие сильные стороны твоей внешности уже являются опорой и как их вывести на первый план;\n\n"
    "— какие зоны заметнее всего ослабляют общее впечатление и как их можно скорректировать;\n\n"
    "— в каком направлении двигаться дальше, чтобы выжать максимум из своей внешности."
    "</blockquote>"
)

BRIEF_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа  ›  Оплата</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Краткий разбор\n\n"
    "💰 <b>Цена</b>  —  199 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "<blockquote>"
    "🔸 <b>Итоговая оценка гармонии:</b>\n"
    "математический балл по геометрии лица — насколько твои пропорции близки к норме.\n\n"
    "🔸 <b>Тир по looksmaxing-шкале:</b>\n"
    "LTN / MTN / HTN / Chadlite / Chad / True Adam — твоя категория внешности.\n\n"
    "🔸 <b>Оценка по ключевым параметрам:</b>\n"
    "глаза, нос, губы, скулы, челюсть, брови, симметрия и баланс — где у тебя сильные стороны и где оценка проседает."
    "</blockquote>\n\n"
    "💡 <b>После оплаты:</b>\n\n"
    "<blockquote>"
    "Просто отправь фото в этот чат —\n"
    "бот автоматически начнёт разбор.\n\n"
    "Готовый PDF-отчёт получишь за 4 минуты."
    "</blockquote>"
)

FULL_TEXT = (
    "📍 <b>Главное меню  ›  Выбор тарифа  ›  Оплата</b>\n\n"
    "<blockquote>"
    "⚜️ <b>План</b>  —  Полный разбор\n\n"
    "💰 <b>Цена</b>  —  499 ₽"
    "</blockquote>\n\n"
    "📚 <b>Что входит в один разбор:</b>\n\n"
    "<blockquote>"
    "🔹 <b>Персональный PDF-отчёт на 25 страниц:</b>\n"
    "полный анализ лица; итоговая оценка гармонии, диаграмма со всеми метриками и визуализация пропорций.\n\n"
    "🔹 <b>Разбор 20 ключевых метрик лица:</b>\n"
    "пропорции твоего лица сравниваются с нормативными значениями из исследования лицевой антропометрии Лесли Фаркаса.\n\n"
    "🔹 <b>Наглядная визуализация измерений:</b>\n"
    "на твоё лицо накладываются 98 ключевых точек, все отрезки и соотношения, по которым считаются пропорции.\n\n"
    "🔹 <b>Понятное объяснение каждой метрики:</b>\n"
    "что именно измеряется, какое значение получилось и как этот показатель влияет на гармонию твоего лица.\n\n"
    "🔹 <b>Конкретные шаги по улучшению:</b>\n"
    "5 советов по самым слабым метрикам и 2 — по уходу; мы расскажем, что менять в первую очередь и что даст максимальный эффект."
    "</blockquote>\n\n"
    "💡 <b>После оплаты:</b>\n\n"
    "<blockquote>"
    "Просто отправь фото в этот чат —\n"
    "бот автоматически начнёт разбор.\n\n"
    "Готовый PDF-отчёт получишь за 4 минуты."
    "</blockquote>"
)

def _grant_text(tier: str) -> str:
    tier_ru = "Краткий разбор" if tier == "brief" else "Полный разбор (25 страниц)"
    tier_emoji = "📋" if tier == "brief" else "📊"
    return (
        f"<blockquote>{tier_emoji} Вам подарен <b>{tier_ru}</b>.</blockquote>\n\n"
        "⚙️ <b>Чтобы разбор был максимально точным:</b>\n\n"
        "<blockquote>"
        "🔹 Фото КАК НА ПАСПОРТ.\n\n"
        "🔹 Смотрите прямо в камеру.\n\n"
        "🔹 Держите голову ровно — без наклонов и поворотов.\n\n"
        "🔹 Не наклоняйте голову к плечу.\n\n"
        "🔹 Уберите волосы с лица — лоб полностью открыт.\n\n"
        "🔹 Сохраняйте нейтральное выражение лица.\n\n"
        "🔹 Обеспечьте ровное освещение без теней.\n\n"
        "🔹 Используйте чёткое фото без размытия."
        "</blockquote>\n\n"
        "‼️ <b>ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ:</b>\n\n"
        "<blockquote>"
        "🔸 ЛИЦО СМОТРИТ СТРОГО ПРЯМО В КАМЕРУ (НЕ ПРОФИЛЬ).\n\n"
        "🔸 Обеспечьте хотя-бы небольшой контраст между подбородком и шеей.\n\n"
        "🔸 Если что-то пошло не так — пишите в техподдержку, мы ОБЯЗАТЕЛЬНО ПОМОЖЕМ! 🤝"
        "</blockquote>\n\n"
        "Просто отправьте фото в ЭТОТ чат —\n"
        "бот автоматически начнёт разбор."
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
    register_user(update.effective_chat.id, user.username or "")
    if user.username:
        save_user_chat_id(user.username, update.effective_chat.id)
    if _is_admin(user):
        save_admin_chat_id(update.effective_chat.id)
        logger.info(f"Admin chat_id: {update.effective_chat.id}")

    example_photo_path = os.path.join(ASSETS_DIR, "example_face.jpg")
    if os.path.exists(example_photo_path):
        with open(example_photo_path, "rb") as f:
            await context.bot.send_photo(
                update.effective_chat.id,
                photo=f,
                caption=_main_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=kb_main(),
            )
    else:
        await update.message.reply_text(
            _main_text(), parse_mode=ParseMode.HTML, reply_markup=kb_main())
    await _send_example_pdfs(update.effective_chat.id, context)


async def _send_example_pdfs(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    for fname, caption, display_name in [
        ("example_brief.pdf", "📋 <b>Краткий разбор</b> — пример отчёта (199 ₽)",
         "Краткий разбор — пример.pdf"),
        ("example_full.pdf",  "📊 <b>Полный разбор</b> — пример отчёта (499 ₽)",
         "Полный разбор — пример.pdf"),
    ]:
        path = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(path):
            with open(path, "rb") as f:
                await context.bot.send_document(
                    chat_id, document=f,
                    filename=display_name,
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
            ANALYZE_TEXT,
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

    args = context.args
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

    # Отправить уведомление пользователю если знаем его chat_id
    user_chat_id = get_chat_id_by_username(username)
    if user_chat_id:
        try:
            await context.bot.send_message(
                user_chat_id,
                _grant_text(tier),
                parse_mode=ParseMode.HTML)
            # Отправляем инструкцию по съёмке
            instr_path = os.path.join(ASSETS_DIR, "instruction.pdf")
            if os.path.exists(instr_path):
                with open(instr_path, "rb") as f:
                    await context.bot.send_document(
                        user_chat_id, document=f,
                        filename="Инструкция по съёмке — Qzels Face Bot.pdf",
                        caption="📸 <b>Инструкция по съёмке</b>\n\nПрочитайте перед отправкой фото для максимально точного результата.",
                        parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Grant notify error for @{username}: {e}")


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
        "📢 <b>Сообщение от Qzels Face Bot:</b>\n\n"
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

    await _forward_to_admin(update, context)

    tier = None
    if _is_admin(user):
        tier = "full"
    else:
        tier = consume_grant(username)

    if not tier:
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
                grant_analysis(username, tier)
            await update.message.reply_text("❌ Анализ не удался. Попробуй другое фото.")
            return

        uname = user.username or user.first_name or "user"

        # ── Предупреждение если определён женский пол ────────────────────────
        if metrics.likely_female:
            await update.message.reply_text(
                "⚠️ <b>Внимание!</b>\n\n"
                "Qzels Face Bot оптимизирован под <b>мужскую</b> геометрию лица — "
                "нормы Фаркаса и все метрики настроены именно под мужские пропорции.\n\n"
                "На твоём фото обнаружены черты, характерные для <b>женского</b> лица. "
                "Разбор будет сравнивать тебя с мужскими нормами, поэтому оценки "
                "могут не отражать реальную привлекательность.\n\n"
                "🚧 <i>Женская версия анализа находится в разработке — "
                "следи за обновлениями!</i>",
                parse_mode=ParseMode.HTML,
            )

        if tier == "brief":
            pdf_b = await loop.run_in_executor(None, generate_brief_pdf, metrics, uname)
            await context.bot.send_document(
                update.effective_chat.id, BytesIO(pdf_b),
                filename="Краткий разбор — Qzels Face Bot.pdf",
                caption="📋 <b>Краткий разбор Qzels Face Bot</b>\n\nСпасибо, что используешь Qzels Face Bot! 🚀",
                parse_mode=ParseMode.HTML)
        else:
            if _is_admin(user):
                pdf_b = await loop.run_in_executor(None, generate_brief_pdf, metrics, uname)
                await context.bot.send_document(
                    update.effective_chat.id, BytesIO(pdf_b),
                    filename="Краткий разбор — Qzels Face Bot.pdf",
                    caption="📋 <b>Краткий разбор</b> (администратор — превью)",
                    parse_mode=ParseMode.HTML)

            pdf_f = await loop.run_in_executor(None, generate_full_pdf, metrics, uname)
            await context.bot.send_document(
                update.effective_chat.id, BytesIO(pdf_f),
                filename="Полный разбор — Qzels Face Bot.pdf",
                caption="📊 <b>Полный разбор Qzels Face Bot</b>",
                parse_mode=ParseMode.HTML)

        increment_daily_count()

    except Exception as e:
        logger.exception(f"Analysis error {user.id}: {e}")
        if not _is_admin(user):
            grant_analysis(username, tier)
        await update.message.reply_text("❌ Что-то пошло не так. Попробуй ещё раз.")


# ════════════════════════════════════════════════════════════════════════════
#  Текстовые сообщения
# ════════════════════════════════════════════════════════════════════════════

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_admin(update.effective_user):
        return
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
    logger.info("Qzels Face Bot запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
