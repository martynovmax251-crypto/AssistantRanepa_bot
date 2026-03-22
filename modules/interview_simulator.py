from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
import json
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class InterviewStates(StatesGroup):
    waiting_for_answer = State()


# База вопросов для интервью
INTERVIEW_QUESTIONS = {
    'python': [
        {
            'question': 'Что такое декораторы в Python? Приведите пример.',
            'answer': 'Декораторы - это функции, которые принимают другую функцию и расширяют её функциональность. Пример:\n@timer\ndef my_function():\n    pass',
            'keywords': ['функция', 'расширяет', '@']
        },
        {
            'question': 'Чем отличается list от tuple?',
            'answer': 'List - изменяемый, tuple - неизменяемый. List использует больше памяти, tuple - меньше.',
            'keywords': ['изменяемый', 'неизменяемый', 'память']
        },
        {
            'question': 'Что такое GIL в Python?',
            'answer': 'Global Interpreter Lock - механизм, который позволяет выполнять только один поток Python за раз, что ограничивает параллелизм.',
            'keywords': ['global', 'interpreter', 'lock', 'поток']
        }
    ],
    'algorithms': [
        {
            'question': 'Объясните сложность быстрой сортировки в лучшем и худшем случае.',
            'answer': 'Лучший: O(n log n), худший: O(n²). Худший случай возникает при уже отсортированном массиве с неудачным выбором опорного элемента.',
            'keywords': ['O(n log n)', 'O(n²)', 'опорный']
        },
        {
            'question': 'Что такое хеш-таблица? Как работает поиск по ключу?',
            'answer': 'Структура данных, использующая хеш-функцию для вычисления индекса. Поиск O(1) в среднем, O(n) в худшем.',
            'keywords': ['хеш', 'индекс', 'O(1)']
        }
    ],
    'system_design': [
        {
            'question': 'Как спроектировать систему сокращения ссылок (как bit.ly)?',
            'answer': 'Использовать хеширование (MD5/SHA) или генератор ID. Нужна БД, кэш (Redis), балансировщик нагрузки.',
            'keywords': ['хеш', 'база', 'кэш', 'балансировка']
        }
    ]
}


@router.message(F.text == "🎤 Interview Simulator")
async def cmd_interview(message: Message):
    """Начать интервью-симулятор"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐍 Python", callback_data="interview_python")],
        [InlineKeyboardButton(text="📊 Алгоритмы", callback_data="interview_algorithms")],
        [InlineKeyboardButton(text="🏗️ System Design", callback_data="interview_system_design")],
        [InlineKeyboardButton(text="🎲 Случайное", callback_data="interview_random")],
        [InlineKeyboardButton(text="📈 Моя статистика", callback_data="interview_stats")]
    ])

    await message.answer(
        "🎤 *Симулятор технического интервью*\n\n"
        "Практикуйтесь в прохождении технических интервью!\n\n"
        "Выберите тему:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("interview_"))
async def start_interview(callback: CallbackQuery, state: FSMContext):
    """Начало интервью"""
    topic = callback.data.split("_")[1]

    if topic == "random":
        topic = random.choice(list(INTERVIEW_QUESTIONS.keys()))

    questions = INTERVIEW_QUESTIONS.get(topic, INTERVIEW_QUESTIONS['python'])
    selected_questions = random.sample(questions, min(3, len(questions)))

    await state.update_data(topic=topic, questions=selected_questions, current=0, score=0)
    await ask_next_question(callback.message, state)


async def ask_next_question(message: Message, state: FSMContext):
    """Задать следующий вопрос"""
    data = await state.get_data()
    current = data['current']
    questions = data['questions']

    if current >= len(questions):
        # Интервью закончено
        await finish_interview(message, state)
        return

    question = questions[current]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Подсказка", callback_data="hint")],
        [InlineKeyboardButton(text="⏭️ Следующий", callback_data="next_question")]
    ])

    await message.answer(
        f"🎤 *Вопрос {current + 1}/{len(questions)}*\n\n"
        f"{question['question']}\n\n"
        f"Введите ваш ответ:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(InterviewStates.waiting_for_answer)


@router.message(InterviewStates.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext):
    """Обработка ответа"""
    data = await state.get_data()
    current = data['current']
    question = data['questions'][current]

    # Оцениваем ответ
    score = evaluate_answer(message.text, question['answer'], question.get('keywords', []))

    # Сохраняем результат
    data['score'] += score
    data['current'] += 1
    await state.update_data(score=data['score'], current=data['current'])

    # Отправляем обратную связь
    feedback = get_feedback(score)

    await message.answer(
        f"📊 *Оценка:* {score}/100\n\n"
        f"{feedback}\n\n"
        f"*Правильный ответ:*\n{question['answer']}"
    )

    # Следующий вопрос
    await ask_next_question(message, state)


def evaluate_answer(answer: str, correct_answer: str, keywords: list) -> int:
    """Оценка ответа"""
    answer_lower = answer.lower()
    correct_lower = correct_answer.lower()

    score = 0

    # Проверка ключевых слов
    for keyword in keywords:
        if keyword.lower() in answer_lower:
            score += 30

    # Проверка длины ответа
    if len(answer.split()) > 20:
        score += 10

    # Проверка на наличие примеров кода
    if 'def' in answer or 'function' in answer or 'class' in answer:
        score += 20

    # Проверка структурированности
    if '\n' in answer or '•' in answer or '-' in answer:
        score += 10

    return min(score, 100)


def get_feedback(score: int) -> str:
    """Получение обратной связи"""
    if score >= 80:
        return "🌟 Отлично! Глубокое понимание темы!"
    elif score >= 60:
        return "👍 Хорошо, но есть что улучшить."
    elif score >= 40:
        return "📚 Неплохо, но нужно больше практики."
    else:
        return "📖 Рекомендую повторить материал."


async def finish_interview(message: Message, state: FSMContext):
    """Завершение интервью"""
    data = await state.get_data()
    score = data['score']
    max_score = len(data['questions']) * 100
    percentage = (score / max_score) * 100

    # Сохраняем результат
    query = """
        INSERT INTO interview_results (user_id, topic, score, total, completed_at)
        VALUES (%s, %s, %s, %s, NOW())
    """
    await db.execute(query, (
        message.from_user.id,
        data['topic'],
        score,
        max_score
    ))

    # Начисляем очки за интервью
    points = int(percentage / 10)  # до 10 очков
    if points > 0:
        await add_points(message.from_user.id, points, f"Интервью по {data['topic']}")

    # Определяем уровень
    if percentage >= 80:
        level = "🌟 Отлично!"
    elif percentage >= 60:
        level = "👍 Хорошо"
    elif percentage >= 40:
        level = "📚 Средний"
    else:
        level = "📖 Начинающий"

    await message.answer(
        f"🎤 *Интервью завершено!*\n\n"
        f"Тема: {data['topic']}\n"
        f"Результат: {score}/{max_score} ({percentage:.1f}%)\n"
        f"Уровень: {level}\n\n"
        f"Получено очков: +{points}\n\n"
        f"Попробуйте пройти интервью по другой теме!"
    )
    await state.clear()