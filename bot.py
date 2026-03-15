#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from config import config
from database.db_config import db
from utils.logger import logger
from modules import error_log, flashcards, pomodoro, project_generator

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем роутеры модулей
dp.include_router(error_log.router)
dp.include_router(flashcards.router)
dp.include_router(pomodoro.router)
dp.include_router(project_generator.router)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Регистрируем пользователя
    query = """
        INSERT INTO users (user_id, username, first_name, last_name, last_active)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        username = username,
        first_name = first_name,
        last_name = last_name,
        last_active = VALUES(last_active)
    """

    await db.execute(query, (
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        datetime.now()
    ))

    # Создаем клавиатуру с основными функциями
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Дневник ошибок")],
            [KeyboardButton(text="🎴 Карточки")],
            [KeyboardButton(text="🍅 Pomodoro"), KeyboardButton(text="💡 Идеи проектов")],
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
        "💡 Находить идеи для проектов\n\n"
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
/stats - Статистика времени

*💡 Идеи проектов:*
/project - Случайная идея
/add_idea - Добавить идею

*Примеры:*
/focus Python
/project
/errors
    """

    await message.answer(help_text, parse_mode="Markdown")


@dp.message()
async def handle_unknown(message: Message):
    """Обработка неизвестных сообщений"""
    await message.answer(
        "Я не понимаю эту команду. Используйте /help для списка доступных команд."
    )


async def set_commands():
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="focus", description="Начать Pomodoro"),
        BotCommand(command="stats", description="Статистика времени"),
        BotCommand(command="project", description="Идея проекта"),
        BotCommand(command="errors", description="Мои ошибки"),
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
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())