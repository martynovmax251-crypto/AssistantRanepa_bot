from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import json
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class CareerStates(StatesGroup):
    adding_company = State()
    adding_position = State()
    adding_date = State()
    adding_notes = State()
    interview_scheduling = State()


@router.message(F.text == "💼 Карьерный трекер")
async def cmd_career(message: Message):
    """Меню карьерного трекера"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить отклик", callback_data="add_application")],
        [InlineKeyboardButton(text="📋 Мои отклики", callback_data="my_applications")],
        [InlineKeyboardButton(text="📅 Собеседования", callback_data="interviews")],
        [InlineKeyboardButton(text="✉️ Шаблоны писем", callback_data="email_templates")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="career_stats")]
    ])

    await message.answer(
        "💼 *Карьерный трекер*\n\n"
        "Отслеживайте процесс поиска работы:\n"
        "• Сохраняйте отклики\n"
        "• Планируйте собеседования\n"
        "• Используйте готовые шаблоны",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "add_application")
async def add_application(callback: CallbackQuery, state: FSMContext):
    """Добавление нового отклика"""
    await callback.message.edit_text(
        "Введите название компании:"
    )
    await state.set_state(CareerStates.adding_company)


@router.message(CareerStates.adding_company)
async def process_company(message: Message, state: FSMContext):
    """Обработка названия компании"""
    await state.update_data(company=message.text)
    await message.answer("Введите название позиции:")
    await state.set_state(CareerStates.adding_position)


@router.message(CareerStates.adding_position)
async def process_position(message: Message, state: FSMContext):
    """Обработка позиции"""
    await state.update_data(position=message.text)
    await message.answer(
        "Введите дату отклика (в формате ДД.ММ.ГГГГ)\n"
        "или нажмите /skip для сегодняшней даты:"
    )
    await state.set_state(CareerStates.adding_date)


@router.message(CareerStates.adding_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты"""
    if message.text == "/skip":
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            date = datetime.strptime(message.text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ или /skip")
            return

    await state.update_data(application_date=date)
    await message.answer("Добавьте заметки (опционально):")
    await state.set_state(CareerStates.adding_notes)


@router.message(CareerStates.adding_notes)
async def process_notes(message: Message, state: FSMContext):
    """Сохранение отклика"""
    data = await state.get_data()

    query = """
        INSERT INTO applications (user_id, company, position, application_date, notes, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
    """
    await db.execute(query, (
        message.from_user.id,
        data['company'],
        data['position'],
        data['application_date'],
        message.text
    ))

    await message.answer(
        f"✅ Отклик в *{data['company']}* сохранен!\n\n"
        f"Статус: ожидание ответа",
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "my_applications")
async def show_applications(callback: CallbackQuery):
    """Показать список откликов"""
    query = """
        SELECT id, company, position, application_date, status, notes
        FROM applications
        WHERE user_id = %s
        ORDER BY application_date DESC
        LIMIT 10
    """
    apps = await db.fetch_all(query, (callback.from_user.id,))

    if not apps:
        await callback.message.edit_text(
            "У вас пока нет сохраненных откликов.\n"
            "Используйте 'Добавить отклик' чтобы начать."
        )
        return

    text = "📋 *Ваши отклики:*\n\n"
    for app in apps:
        status_emoji = get_status_emoji(app['status'])
        date = app['application_date'].strftime("%d.%m.%Y")
        text += f"{status_emoji} *{app['company']}* - {app['position']}\n"
        text += f"   📅 {date} | Статус: {app['status']}\n"
        if app['notes']:
            text += f"   📝 {app['notes'][:50]}...\n"
        text += "\n"

    await callback.message.edit_text(text, parse_mode="Markdown")


@router.callback_query(F.data == "interviews")
async def show_interviews(callback: CallbackQuery):
    """Показать предстоящие собеседования"""
    query = """
        SELECT i.*, a.company, a.position
        FROM interviews i
        JOIN applications a ON i.application_id = a.id
        WHERE i.user_id = %s AND i.interview_date >= NOW()
        ORDER BY i.interview_date ASC
        LIMIT 5
    """
    interviews = await db.fetch_all(query, (callback.from_user.id,))

    if not interviews:
        await callback.message.edit_text(
            "У вас нет предстоящих собеседований.\n"
            "Добавьте отклик и запланируйте собеседование!"
        )
        return

    text = "📅 *Предстоящие собеседования:*\n\n"
    for interview in interviews:
        date = interview['interview_date'].strftime("%d.%m.%Y %H:%M")
        text += f"🏢 *{interview['company']}* - {interview['position']}\n"
        text += f"   📅 {date}\n"
        text += f"   📍 {interview['type']}\n"
        text += f"   💡 {interview['notes'] or 'Нет заметок'}\n\n"

    await callback.message.edit_text(text, parse_mode="Markdown")


@router.callback_query(F.data == "email_templates")
async def show_templates(callback: CallbackQuery):
    """Показать шаблоны писем"""
    templates = {
        "cover_letter": "✉️ *Шаблон сопроводительного письма*\n\n"
                        "Уважаемая команда [Компания],\n\n"
                        "Меня зовут [Имя], и я хочу предложить свою кандидатуру на вакансию [Позиция]. "
                        "Я [кратко о себе и опыте].\n\n"
                        "Мои ключевые навыки:\n"
                        "• [Навык 1]\n"
                        "• [Навык 2]\n"
                        "• [Навык 3]\n\n"
                        "Буду рад возможности пройти собеседование.\n\n"
                        "С уважением,\n"
                        "[Имя]\n"
                        "[Ссылка на GitHub/LinkedIn]",

        "follow_up": "📧 *Шаблон для follow-up*\n\n"
                     "Уважаемая команда [Компания],\n\n"
                     "Меня зовут [Имя]. Я откликался на вакансию [Позиция] [дата отклика].\n\n"
                     "Хотел бы уточнить статус рассмотрения моей кандидатуры. "
                     "Буду признателен за обратную связь.\n\n"
                     "С уважением,\n"
                     "[Имя]",

        "thank_you": "💌 *Шаблон благодарности после собеседования*\n\n"
                     "Уважаемый/ая [Имя рекрутера],\n\n"
                     "Благодарю вас за возможность пройти собеседование на позицию [Позиция]. "
                     "Мне было очень интересно узнать больше о проектах [Компания].\n\n"
                     "Особенно меня заинтересовал [что-то из разговора].\n\n"
                     "Буду рад продолжить общение.\n\n"
                     "С уважением,\n"
                     "[Имя]"
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Сопроводительное письмо", callback_data="template_cover")],
        [InlineKeyboardButton(text="🔄 Follow-up письмо", callback_data="template_follow")],
        [InlineKeyboardButton(text="🙏 Благодарность", callback_data="template_thanks")]
    ])

    await callback.message.edit_text(
        "Выберите шаблон письма:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("template_"))
async def show_template(callback: CallbackQuery):
    """Показать выбранный шаблон"""
    template_type = callback.data.split("_")[1]

    templates = {
        "cover": "cover_letter",
        "follow": "follow_up",
        "thanks": "thank_you"
    }

    template_name = templates.get(template_type)
    if template_name:
        template = show_templates.__code__.co_consts[0][template_name]
        await callback.message.edit_text(template, parse_mode="Markdown")


def get_status_emoji(status: str) -> str:
    """Эмодзи статуса"""
    return {
        'pending': '⏳',
        'review': '👀',
        'interview': '📅',
        'rejected': '❌',
        'offer': '🎉'
    }.get(status, '⚪')