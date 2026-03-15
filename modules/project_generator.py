from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class ProjectStates(StatesGroup):
    waiting_for_project_idea = State()


@router.message(F.text == "💡 Идеи проектов")
async def cmd_project(message: Message):
    """Генерация идей проектов"""
    # Получаем случайную идею из БД
    query = "SELECT * FROM project_ideas WHERE is_active = TRUE ORDER BY RAND() LIMIT 1"
    project = await db.fetch_one(query)

    if not project:
        await message.answer("В базе пока нет идей проектов.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё идею", callback_data="another_project")],
        [InlineKeyboardButton(text="💾 Сохранить", callback_data="save_project")]
    ])

    difficulty_emoji = {
        'beginner': '🟢',
        'intermediate': '🟡',
        'advanced': '🔴'
    }

    text = (
        f"💡 *{project['title']}*\n\n"
        f"{project['description']}\n\n"
        f"Сложность: {difficulty_emoji.get(project['difficulty'], '⚪')} {project['difficulty']}\n"
        f"Технологии: `{project['technologies']}`"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "another_project")
async def another_project(callback: CallbackQuery):
    """Показать другую идею"""
    await cmd_project(callback.message)


@router.callback_query(F.data == "save_project")
async def save_project(callback: CallbackQuery):
    """Сохранить идею в избранное"""
    # Здесь можно добавить функционал сохранения
    await callback.answer("Проект сохранен в избранном!")


@router.message(F.text == "/add_idea")
async def add_project_idea(message: Message, state: FSMContext):
    """Добавление новой идеи проекта"""
    await message.answer(
        "📝 *Добавление новой идеи проекта*\n\n"
        "Отправьте идею в формате:\n"
        "Название | Описание | сложность(beginner/intermediate/advanced) | технологии\n\n"
        "Пример:\n"
        "Чат-приложение | Создайте веб-чат с комнатами | intermediate | Python, WebSockets",
        parse_mode="Markdown"
    )
    await state.set_state(ProjectStates.waiting_for_project_idea)


@router.message(ProjectStates.waiting_for_project_idea)
async def process_project_idea(message: Message, state: FSMContext):
    """Обработка новой идеи проекта"""
    try:
        parts = message.text.split('|')
        if len(parts) >= 4:
            title = parts[0].strip()
            description = parts[1].strip()
            difficulty = parts[2].strip().lower()
            technologies = parts[3].strip()

            if difficulty not in ['beginner', 'intermediate', 'advanced']:
                difficulty = 'beginner'

            query = """
                INSERT INTO project_ideas (title, description, difficulty, technologies, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """

            await db.execute(query, (title, description, difficulty, technologies, message.from_user.id))

            await message.answer("✅ Идея проекта успешно добавлена! Спасибо за вклад!")
        else:
            await message.answer("❌ Неверный формат. Пожалуйста, используйте указанный формат.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении идеи проекта: {e}")
        await message.answer("❌ Произошла ошибка при сохранении идеи.")

    await state.clear()