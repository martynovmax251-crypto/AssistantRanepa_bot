from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import logging
from database.db_config import db
from utils.ocr_helper import ocr_helper
from utils.validators import validators
from config import config

logger = logging.getLogger(__name__)
router = Router()


class ErrorStates(StatesGroup):
    waiting_for_error = State()
    waiting_for_subject = State()
    waiting_for_solution = State()


@router.message(F.text == "📝 Дневник ошибок")
async def cmd_error_log(message: Message, state: FSMContext):
    """Начало работы с дневником ошибок"""
    await message.answer(
        "📝 *Дневник ошибок*\n\n"
        "Опишите ошибку или отправьте скриншот с кодом ошибки:\n"
        "(или отправьте /cancel для отмены)",
        parse_mode="Markdown"
    )
    await state.set_state(ErrorStates.waiting_for_error)


@router.message(ErrorStates.waiting_for_error)
async def process_error_input(message: Message, state: FSMContext):
    """Обработка текста или скриншота ошибки"""
    error_text = ""

    if message.photo:
        # Обработка скриншота
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        photo_bytes = await message.bot.download_file(file_info.file_path)

        # OCR распознавание
        error_text = await ocr_helper.extract_code_from_screenshot(photo_bytes.read())
        await message.answer("📸 Скриншот обработан. Текст ошибки распознан.")
    elif message.text:
        error_text = message.text
    else:
        await message.answer("Пожалуйста, отправьте текст или скриншот ошибки.")
        return

    if not error_text:
        await message.answer("Не удалось распознать ошибку. Попробуйте ещё раз.")
        return

    # Сохраняем ошибку
    error_text = validators.sanitize_text(error_text, 2000)

    query = """
        INSERT INTO error_logs (user_id, error_text, created_at, next_review)
        VALUES (%s, %s, %s, %s)
    """

    next_review = datetime.now() + timedelta(days=1)
    await db.execute(query, (message.from_user.id, error_text, datetime.now(), next_review))

    await state.update_data(error_text=error_text)
    await message.answer(
        "✅ Ошибка сохранена!\n\n"
        "Укажите предмет (например: Python, JavaScript, SQL и т.д.):\n"
        "(или отправьте 'другое')"
    )
    await state.set_state(ErrorStates.waiting_for_subject)


@router.message(ErrorStates.waiting_for_subject)
async def process_error_subject(message: Message, state: FSMContext):
    """Обработка предмета ошибки"""
    subject = validators.validate_subject(message.text)

    data = await state.get_data()

    query = """
        UPDATE error_logs 
        SET subject = %s 
        WHERE user_id = %s AND error_text = %s AND subject IS NULL
        ORDER BY created_at DESC LIMIT 1
    """

    await db.execute(query, (subject, message.from_user.id, data['error_text']))

    await message.answer(
        "Теперь опишите решение ошибки (можно отправить позже командой /solve):\n"
        "или отправьте 'пропустить'"
    )
    await state.set_state(ErrorStates.waiting_for_solution)


@router.message(ErrorStates.waiting_for_solution)
async def process_error_solution(message: Message, state: FSMContext):
    """Обработка решения ошибки"""
    if message.text.lower() != 'пропустить':
        data = await state.get_data()
        solution = validators.sanitize_text(message.text, 2000)

        query = """
            UPDATE error_logs 
            SET solution_text = %s, solved_at = %s, is_resolved = TRUE
            WHERE user_id = %s AND error_text = %s AND solution_text IS NULL
            ORDER BY created_at DESC LIMIT 1
        """

        await db.execute(query, (solution, datetime.now(), message.from_user.id, data['error_text']))
        await message.answer("✅ Решение сохранено!")

    await message.answer(
        "📊 *Ошибка полностью сохранена!*\n\n"
        "Я буду периодически напоминать вам о ней для повторения.",
        parse_mode="Markdown"
    )
    await state.clear()


@router.message(F.text == "/errors")
async def show_my_errors(message: Message):
    """Показать список ошибок пользователя"""
    query = """
        SELECT id, error_text, subject, created_at, is_resolved
        FROM error_logs
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """

    errors = await db.fetch_all(query, (message.from_user.id,))

    if not errors:
        await message.answer("У вас пока нет сохраненных ошибок.")
        return

    text = "📋 *Последние ошибки:*\n\n"
    for error in errors:
        status = "✅" if error['is_resolved'] else "❌"
        date = error['created_at'].strftime("%d.%m.%Y")
        subject = error['subject'] or "без темы"
        text += f"{status} [{date}] *{subject}*: {error['error_text'][:50]}...\n"

    await message.answer(text, parse_mode="Markdown")


async def check_errors_for_review():
    """Проверка ошибок для повторения (запускается по расписанию)"""
    query = """
        SELECT user_id, id, error_text, solution_text
        FROM error_logs
        WHERE next_review <= NOW() AND is_resolved = TRUE
    """

    errors = await db.fetch_all(query)

    for error in errors:
        # Здесь должен быть код для отправки уведомления пользователю
        # через бота (нужен доступ к боту)
        pass