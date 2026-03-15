from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import random
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class FlashcardStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_answer = State()
    waiting_for_category = State()
    reviewing = State()


@router.message(F.text == "🎴 Карточки")
async def cmd_flashcards(message: Message):
    """Меню карточек"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать карточку", callback_data="create_card")],
        [InlineKeyboardButton(text="📚 Начать повторение", callback_data="start_review")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="card_stats")]
    ])

    await message.answer(
        "🎴 *Режим карточек*\n\n"
        "Здесь вы можете создавать карточки с вопросами и ответами "
        "для эффективного запоминания материала.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "create_card")
async def create_card(callback: CallbackQuery, state: FSMContext):
    """Создание новой карточки"""
    await callback.message.edit_text(
        "📝 Введите вопрос для карточки:"
    )
    await state.set_state(FlashcardStates.waiting_for_question)


@router.message(FlashcardStates.waiting_for_question)
async def process_card_question(message: Message, state: FSMContext):
    """Обработка вопроса карточки"""
    await state.update_data(question=message.text)
    await message.answer(
        "✍️ Теперь введите ответ на вопрос:"
    )
    await state.set_state(FlashcardStates.waiting_for_answer)


@router.message(FlashcardStates.waiting_for_answer)
async def process_card_answer(message: Message, state: FSMContext):
    """Обработка ответа карточки"""
    await state.update_data(answer=message.text)
    await message.answer(
        "🏷️ Введите категорию (например: Python, Algorithms, SQL):"
    )
    await state.set_state(FlashcardStates.waiting_for_category)


@router.message(FlashcardStates.waiting_for_category)
async def process_card_category(message: Message, state: FSMContext):
    """Обработка категории и сохранение карточки"""
    data = await state.get_data()

    query = """
        INSERT INTO flashcards 
        (user_id, question, answer, category, created_at, next_review)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    now = datetime.now()
    await db.execute(query, (
        message.from_user.id,
        data['question'],
        data['answer'],
        message.text,
        now,
        now  # сразу доступно для повторения
    ))

    await message.answer(
        "✅ *Карточка создана!*\n\n"
        "Она будет доступна для повторения.",
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "start_review")
async def start_review(callback: CallbackQuery):
    """Начать повторение карточек"""
    query = """
        SELECT id, question, answer, ease_factor, interval_days, repetitions
        FROM flashcards
        WHERE user_id = %s AND next_review <= NOW()
        ORDER BY next_review ASC
        LIMIT 1
    """

    card = await db.fetch_one(query, (callback.from_user.id,))

    if not card:
        await callback.message.edit_text(
            "🎉 Отлично! На сегодня все карточки повторены.\n"
            "Приходите завтра для новых повторений!"
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁️ Показать ответ", callback_data=f"show_answer_{card['id']}")],
        [InlineKeyboardButton(text="🚫 Закончить", callback_data="stop_review")]
    ])

    await callback.message.edit_text(
        f"❓ *Вопрос:*\n{card['question']}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("show_answer_"))
async def show_answer(callback: CallbackQuery):
    """Показать ответ на карточку"""
    card_id = int(callback.data.split("_")[2])

    query = "SELECT answer FROM flashcards WHERE id = %s"
    card = await db.fetch_one(query, (card_id,))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Легко", callback_data=f"review_{card_id}_easy"),
            InlineKeyboardButton(text="⚖️ Средне", callback_data=f"review_{card_id}_medium"),
            InlineKeyboardButton(text="❌ Тяжело", callback_data=f"review_{card_id}_hard")
        ],
        [InlineKeyboardButton(text="📖 Следующая", callback_data="start_review")]
    ])

    await callback.message.edit_text(
        f"*Ответ:*\n{card['answer']}\n\n"
        f"Оцените сложность:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("review_"))
async def process_review(callback: CallbackQuery):
    """Обработка результата повторения"""
    parts = callback.data.split("_")
    card_id = int(parts[1])
    quality = parts[2]  # easy, medium, hard

    # Получаем текущие данные карточки
    query = "SELECT * FROM flashcards WHERE id = %s"
    card = await db.fetch_one(query, (card_id,))

    # Алгоритм интервальных повторений (SM-2)
    ease_factor = card['ease_factor']
    repetitions = card['repetitions']

    # Конвертируем качество ответа в число
    if quality == "easy":
        q = 5
    elif quality == "medium":
        q = 3
    else:
        q = 1

    if q >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 3
        else:
            interval = int(card['interval_days'] * ease_factor)

        repetitions += 1
    else:
        interval = 1
        repetitions = 0

    # Обновляем ease_factor
    ease_factor = max(1.3, ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))

    # Вычисляем дату следующего повторения
    next_review = datetime.now() + timedelta(days=interval)

    # Обновляем карточку
    update_query = """
        UPDATE flashcards 
        SET ease_factor = %s, interval_days = %s, repetitions = %s,
            next_review = %s, last_reviewed = %s,
            total_reviews = total_reviews + 1,
            correct_reviews = correct_reviews + %s
        WHERE id = %s
    """

    await db.execute(update_query, (
        ease_factor, interval, repetitions,
        next_review, datetime.now(),
        1 if q >= 3 else 0,
        card_id
    ))

    await callback.answer("Результат сохранен!")

    # Показываем следующую карточку
    await start_review(callback)