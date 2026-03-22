#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from config import config
from database.db_config import db
from utils.logger import logger

# Импортируем все модули
from modules import (
    error_log,
    flashcards,
    pomodoro,
    project_generator,
    code_review,
    leetcode_tracker,
    career_tracker,
    team_up,
    achievements,
    interview_simulator
)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем все роутеры модулей
dp.include_router(error_log.router)
dp.include_router(flashcards.router)
dp.include_router(pomodoro.router)
dp.include_router(project_generator.router)
dp.include_router(code_review.router)
dp.include_router(leetcode_tracker.router)
dp.include_router(career_tracker.router)
dp.include_router(team_up.router)
dp.include_router(achievements.router)
dp.include_router(interview_simulator.router)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Регистрируем пользователя
    query = """
        INSERT INTO users (user_id, username, first_name, last_name, last_active)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        username = VALUES(username),
        first_name = VALUES(first_name),
        last_name = VALUES(last_name),
        last_active = VALUES(last_active)
    """

    await db.execute(query, (
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        datetime.now()
    ))

    # Создаем клавиатуру с основными функциями (расширенная версия)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Дневник ошибок"), KeyboardButton(text="🎴 Карточки")],
            [KeyboardButton(text="🍅 Pomodoro"), KeyboardButton(text="💡 Идеи проектов")],
            [KeyboardButton(text="🔍 Код-ревью"), KeyboardButton(text="📊 LeetCode Tracker")],
            [KeyboardButton(text="💼 Карьерный трекер"), KeyboardButton(text="👥 Team Up")],
            [KeyboardButton(text="🎖️ Достижения"), KeyboardButton(text="🎤 Interview Simulator")],
            [KeyboardButton(text="/stats"), KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "👋 *Привет! Я твой персональный IT-ассистент!*\n\n"
        "Я помогу тебе:\n"
        "📝 Вести дневник ошибок\n"
        "🎴 Учить материал с карточками\n"
        "🍅 Фокусироваться с Pomodoro\n"
        "💡 Находить идеи для проектов\n"
        "🔍 Анализировать код\n"
        "📊 Трекать решение задач\n"
        "💼 Управлять карьерой\n"
        "👥 Находить напарников\n"
        "🎖️ Получать достижения\n"
        "🎤 Тренироваться к собеседованиям\n\n"
        "Выбери нужный модуль или используй /help для справки.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📚 *Доступные команды:*

*Основные:*
/start - Начать работу
/help - Показать эту справку

*📝 Дневник ошибок:*
Отправьте текст ошибки или скриншот
/errors - Показать мои ошибки

*🎴 Карточки:*
/create_card - Создать карточку
/review - Начать повторение

*🍅 Pomodoro:*
/focus [тема] - Начать фокус-сессию
/stop - Прервать сессию
/stats - Статистика времени

*💡 Идеи проектов:*
/project - Случайная идея
/add_idea - Добавить идею

*🔍 Код-ревью:*
Отправьте код для анализа
Поддерживаются: Python, JavaScript, Java, C++

*📊 LeetCode Tracker:*
/daily - Ежедневная задача
/challenge - Начать челлендж
/leetcode_stats - Моя статистика

*💼 Карьерный трекер:*
/application - Добавить отклик
/interviews - Предстоящие собеседования
/templates - Шаблоны писем

*👥 Team Up:*
/find_partner - Найти напарника
/create_challenge - Создать челлендж
/study_room - Виртуальная комната

*🎖️ Достижения:*
/achievements - Мои достижения
/leaderboard - Таблица лидеров

*🎤 Interview Simulator:*
/interview [тема] - Начать интервью
/interview_stats - Статистика

*Примеры использования:*
/focus Python
/project
/errors
/daily
/interview python
    """

    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("stats"))
async def show_stats(message: Message):
    """Показать общую статистику пользователя"""
    # Статистика по Pomodoro
    query = """
        SELECT COUNT(*) as sessions, SUM(duration_minutes) as total_minutes
        FROM pomodoro_sessions
        WHERE user_id = %s AND completed_at IS NOT NULL
    """
    pomodoro_stats = await db.fetch_one(query, (message.from_user.id,))

    # Статистика по карточкам
    query = """
        SELECT COUNT(*) as total, SUM(correct_reviews) as correct
        FROM flashcards
        WHERE user_id = %s
    """
    flashcard_stats = await db.fetch_one(query, (message.from_user.id,))

    # Статистика по ошибкам
    query = """
        SELECT COUNT(*) as total, SUM(is_resolved) as resolved
        FROM error_logs
        WHERE user_id = %s
    """
    error_stats = await db.fetch_one(query, (message.from_user.id,))

    # Статистика по LeetCode
    query = """
        SELECT COUNT(*) as solved
        FROM daily_tasks
        WHERE user_id = %s AND solved = TRUE
    """
    leetcode_stats = await db.fetch_one(query, (message.from_user.id,))

    # Статистика по код-ревью
    query = """
        SELECT AVG(score) as avg_score, COUNT(*) as total
        FROM code_review_stats
        WHERE user_id = %s
    """
    review_stats = await db.fetch_one(query, (message.from_user.id,))

    # Общие очки
    query = """
        SELECT SUM(points) as total_points
        FROM user_points
        WHERE user_id = %s
    """
    points_stats = await db.fetch_one(query, (message.from_user.id,))

    text = "📊 *Ваша общая статистика*\n\n"

    # Pomodoro
    sessions = pomodoro_stats['sessions'] or 0
    hours = (pomodoro_stats['total_minutes'] or 0) / 60
    text += f"🍅 *Pomodoro:* {sessions} сессий, {hours:.1f} часов\n"

    # Карточки
    total_cards = flashcard_stats['total'] or 0
    correct = flashcard_stats['correct'] or 0
    text += f"🎴 *Карточки:* {total_cards} карточек, {correct} правильных ответов\n"

    # Ошибки
    total_errors = error_stats['total'] or 0
    resolved = error_stats['resolved'] or 0
    text += f"📝 *Ошибки:* {total_errors} сохранено, {resolved} решено\n"

    # LeetCode
    solved = leetcode_stats['solved'] or 0
    text += f"📊 *LeetCode:* {solved} решенных задач\n"

    # Код-ревью
    total_reviews = review_stats['total'] or 0
    avg_score = review_stats['avg_score'] or 0
    text += f"🔍 *Код-ревью:* {total_reviews} проверок, средний балл: {avg_score:.1f}\n"

    # Очки
    points = points_stats['total_points'] or 0
    text += f"\n🏆 *Всего очков:* {points}\n"

    # Уровень
    if points < 100:
        level = "🌱 Начинающий"
    elif points < 500:
        level = "📚 Продолжающий"
    elif points < 1000:
        level = "⚡ Продвинутый"
    elif points < 2000:
        level = "🔥 Эксперт"
    else:
        level = "🏆 Мастер"

    text += f"📈 *Уровень:* {level}"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    """Ежедневная задача (быстрый доступ к LeetCode)"""
    await leetcode_tracker.get_daily_task(message)


@dp.message(Command("challenge"))
async def cmd_challenge(message: Message):
    """Начать челлендж (быстрый доступ к Team Up)"""
    await team_up.cmd_team_up(message)


@dp.message(Command("application"))
async def cmd_application(message: Message):
    """Добавить отклик (быстрый доступ к карьерному трекеру)"""
    await career_tracker.cmd_career(message)


@dp.message(Command("interviews"))
async def cmd_interviews(message: Message):
    """Показать собеседования"""
    await career_tracker.show_interviews(message)


@dp.message(Command("templates"))
async def cmd_templates(message: Message):
    """Показать шаблоны писем"""
    await career_tracker.show_templates(message)


@dp.message(Command("achievements"))
async def cmd_achievements(message: Message):
    """Показать достижения"""
    await achievements.cmd_achievements(message)


@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message):
    """Показать таблицу лидеров"""
    await achievements.show_leaderboard(message)


@dp.message(Command("interview"))
async def cmd_interview(message: Message):
    """Начать интервью"""
    topic = message.text.replace("/interview", "").strip()
    if topic:
        await interview_simulator.start_interview_with_topic(message, topic)
    else:
        await interview_simulator.cmd_interview(message)


@dp.message(Command("interview_stats"))
async def cmd_interview_stats(message: Message):
    """Показать статистику интервью"""
    await interview_simulator.show_interview_stats(message)


@dp.message(Command("find_partner"))
async def cmd_find_partner(message: Message):
    """Найти напарника"""
    await team_up.cmd_team_up(message)


@dp.message(Command("create_challenge"))
async def cmd_create_challenge(message: Message):
    """Создать челлендж"""
    await team_up.create_challenge(message)


@dp.message(Command("study_room"))
async def cmd_study_room(message: Message):
    """Виртуальная комната для учебы"""
    await team_up.study_room(message)


@dp.message(Command("leetcode_stats"))
async def cmd_leetcode_stats(message: Message):
    """Показать статистику LeetCode"""
    await leetcode_tracker.show_leetcode_stats(message)


@dp.message(Command("code_review"))
async def cmd_code_review(message: Message):
    """Начать код-ревью"""
    await code_review.cmd_code_review(message)


@dp.message()
async def handle_unknown(message: Message):
    """Обработка неизвестных сообщений"""
    await message.answer(
        "Я не понимаю эту команду. Используйте /help для списка доступных команд.\n\n"
        "Или нажмите на кнопки в меню для выбора модуля."
    )


async def set_commands():
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="focus", description="Начать Pomodoro"),
        BotCommand(command="stats", description="Общая статистика"),
        BotCommand(command="project", description="Идея проекта"),
        BotCommand(command="errors", description="Мои ошибки"),
        BotCommand(command="daily", description="Ежедневная задача"),
        BotCommand(command="interview", description="Симуляция интервью"),
        BotCommand(command="achievements", description="Мои достижения"),
        BotCommand(command="leaderboard", description="Таблица лидеров")
    ]
    await bot.set_my_commands(commands)


async def shutdown():
    """Завершение работы"""
    logger.info("Завершение работы бота...")
    await db.close()
    await bot.session.close()


async def main():
    """Основная функция"""
    try:
        logger.info("Запуск бота...")

        # Подключаемся к БД
        await db.connect()
        logger.info("Подключение к БД успешно")

        # Устанавливаем команды
        await set_commands()

        # Запускаем бота
        await dp.start_polling(bot, skip_updates=True)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())