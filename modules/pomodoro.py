from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import asyncio
import logging
from database.db_config import db
from config import config

logger = logging.getLogger(__name__)
router = Router()

active_sessions = {}  # user_id: task


class PomodoroStates(StatesGroup):
    working = State()
    break_time = State()
    waiting_for_github = State()


@router.message(F.text == "🍅 Pomodoro")
async def cmd_pomodoro(message: Message):
    """Запуск Pomodoro"""
    if message.from_user.id in active_sessions:
        await message.answer("У вас уже есть активная сессия! Завершите её командой /stop")
        return

    await message.answer(
        "🍅 *Pomodoro таймер*\n\n"
        "Введите тему, над которой будете работать:\n"
        "(например: /focus Python проект)",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/focus"))
async def start_focus(message: Message, state: FSMContext):
    """Запуск фокус-сессии"""
    topic = message.text.replace("/focus", "").strip()
    if not topic:
        await message.answer("Пожалуйста, укажите тему. Например: /focus Python")
        return

    # Создаем запись в БД
    query = """
        INSERT INTO pomodoro_sessions (user_id, topic, duration_minutes, started_at, status)
        VALUES (%s, %s, %s, %s, 'active')
    """

    await db.execute(query, (
        message.from_user.id,
        topic,
        config.POMODORO_WORK_TIME,
        datetime.now()
    ))

    await message.answer(
        f"🍅 *Сессия началась!*\n"
        f"Тема: {topic}\n"
        f"Время: {config.POMODORO_WORK_TIME} минут\n\n"
        f"Я буду игнорировать ваши сообщения до окончания сессии.",
        parse_mode="Markdown"
    )

    await state.set_state(PomodoroStates.working)
    await state.update_data(topic=topic)

    # Запускаем таймер
    task = asyncio.create_task(pomodoro_timer(message, state))
    active_sessions[message.from_user.id] = task


async def pomodoro_timer(message: Message, state: FSMContext):
    """Таймер Pomodoro"""
    try:
        await asyncio.sleep(config.POMODORO_WORK_TIME * 60)

        # Время вышло
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Загрузить коммит", callback_data="add_commit")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_commit")]
        ])

        await message.answer(
            "⏰ *Время вышло!*\n\n"
            "Загрузили код на GitHub? Поделитесь ссылкой на коммит:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        await state.set_state(PomodoroStates.waiting_for_github)

    except asyncio.CancelledError:
        logger.info(f"Pomodoro сессия для пользователя {message.from_user.id} прервана")
        raise


@router.message(PomodoroStates.working)
async def ignore_messages(message: Message):
    """Игнорирование сообщений во время работы"""
    await message.answer(
        "🔇 Режим фокуса активен!\n"
        "Дождитесь окончания сессии или используйте /stop для прерывания."
    )


@router.callback_query(F.data == "add_commit")
async def add_github_commit(callback: CallbackQuery, state: FSMContext):
    """Добавление ссылки на коммит"""
    await callback.message.edit_text(
        "Отправьте ссылку на GitHub коммит:"
    )
    await state.set_state(PomodoroStates.waiting_for_github)


@router.message(PomodoroStates.waiting_for_github)
async def process_github_commit(message: Message, state: FSMContext):
    """Обработка ссылки на коммит"""
    # Обновляем последнюю сессию пользователя
    query = """
        UPDATE pomodoro_sessions 
        SET completed_at = %s, status = 'completed', github_commit_url = %s
        WHERE user_id = %s AND status = 'active'
        ORDER BY started_at DESC LIMIT 1
    """

    await db.execute(query, (datetime.now(), message.text, message.from_user.id))

    # Удаляем из активных сессий
    if message.from_user.id in active_sessions:
        del active_sessions[message.from_user.id]

    await message.answer(
        "✅ *Сессия завершена!*\n\n"
        "Отличная работа! Хотите сделать перерыв?",
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(F.text == "/stats")
async def show_statistics(message: Message):
    """Показать статистику Pomodoro"""
    query = """
        SELECT topic, COUNT(*) as sessions, SUM(duration_minutes) as total_minutes
        FROM pomodoro_sessions
        WHERE user_id = %s AND completed_at IS NOT NULL
        GROUP BY topic
        ORDER BY total_minutes DESC
        LIMIT 10
    """

    stats = await db.fetch_all(query, (message.from_user.id,))

    if not stats:
        await message.answer("У вас пока нет завершенных Pomodoro сессий.")
        return

    text = "📊 *Статистика Pomodoro:*\n\n"
    total_hours = 0

    for stat in stats:
        hours = stat['total_minutes'] / 60
        total_hours += hours
        text += f"• *{stat['topic']}*: {hours:.1f} ч ({stat['sessions']} сессий)\n"

    text += f"\n*Всего:* {total_hours:.1f} часов"

    await message.answer(text, parse_mode="Markdown")