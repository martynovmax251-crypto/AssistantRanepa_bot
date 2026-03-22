from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class TeamStates(StatesGroup):
    looking_for_team = State()
    creating_challenge = State()


@router.message(F.text == "👥 Team Up")
async def cmd_team_up(message: Message):
    """Меню поиска напарников"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти напарника", callback_data="find_partner")],
        [InlineKeyboardButton(text="🏆 Создать челлендж", callback_data="create_challenge")],
        [InlineKeyboardButton(text="📋 Активные челленджи", callback_data="active_challenges")],
        [InlineKeyboardButton(text="💬 Study Room", callback_data="study_room")]
    ])

    await message.answer(
        "👥 *Team Up*\n\n"
        "Найдите напарников для совместного обучения!\n\n"
        "• Найти напарника — подберите партнера по интересам\n"
        "• Челленджи — соревнуйтесь с командой\n"
        "• Study Room — виртуальные комнаты для учебы",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "find_partner")
async def find_partner(callback: CallbackQuery, state: FSMContext):
    """Поиск напарника"""
    await callback.message.edit_text(
        "Расскажите о себе:\n"
        "• Какие технологии изучаете?\n"
        "• Какой уровень?\n"
        "• В каком направлении хотите развиваться?\n\n"
        "Напишите описание и я найду подходящих напарников:"
    )
    await state.set_state(TeamStates.looking_for_team)


@router.message(TeamStates.looking_for_team)
async def process_partner_search(message: Message, state: FSMContext):
    """Обработка поиска напарника"""
    description = message.text

    # Сохраняем профиль
    query = """
        INSERT INTO user_profiles (user_id, description, looking_for, updated_at)
        VALUES (%s, %s, 'team', NOW())
        ON DUPLICATE KEY UPDATE
        description = VALUES(description),
        looking_for = 'team',
        updated_at = NOW()
    """
    await db.execute(query, (message.from_user.id, description))

    # Ищем похожих пользователей
    query = """
        SELECT user_id, description
        FROM user_profiles
        WHERE looking_for = 'team' AND user_id != %s
        ORDER BY updated_at DESC
        LIMIT 5
    """
    partners = await db.fetch_all(query, (message.from_user.id,))

    if not partners:
        await message.answer(
            "Пока нет подходящих напарников. Я уведомлю вас, когда кто-то появится!\n\n"
            "А пока можете создать челлендж или присоединиться к study room."
        )
        await state.clear()
        return

    text = "🔍 *Найдены потенциальные напарники:*\n\n"
    for partner in partners:
        text += f"👤 Пользователь\n"
        text += f"📝 {partner['description'][:100]}...\n\n"

    text += "Напишите /connect [user_id] чтобы связаться с напарником."

    await message.answer(text, parse_mode="Markdown")
    await state.clear()


@router.callback_query(F.data == "create_challenge")
async def create_challenge(callback: CallbackQuery, state: FSMContext):
    """Создание челленджа"""
    await callback.message.edit_text(
        "🏆 *Создание челленджа*\n\n"
        "Введите название челленджа:"
    )
    await state.set_state(TeamStates.creating_challenge)


@router.message(TeamStates.creating_challenge)
async def process_challenge_name(message: Message, state: FSMContext):
    """Обработка названия челленджа"""
    await state.update_data(challenge_name=message.text)
    await message.answer(
        "Какое задание?\n"
        "Например: 'Решить 10 задач LeetCode', 'Сделать пет-проект', 'Изучить React'"
    )
    await state.set_state(TeamStates.creating_challenge, 'task')


@router.message(TeamStates.creating_challenge)
async def process_challenge_task(message: Message, state: FSMContext):
    """Обработка задания"""
    data = await state.get_data()

    query = """
        INSERT INTO challenges (creator_id, name, task, created_at, status)
        VALUES (%s, %s, %s, NOW(), 'active')
    """
    await db.execute(query, (message.from_user.id, data['challenge_name'], message.text))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Присоединиться", callback_data=f"join_challenge")],
        [InlineKeyboardButton(text="📢 Поделиться", callback_data="share_challenge")]
    ])

    await message.answer(
        f"✅ *Челлендж '{data['challenge_name']}' создан!*\n\n"
        f"Задание: {message.text}\n\n"
        f"Приглашайте друзей присоединиться!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.clear()