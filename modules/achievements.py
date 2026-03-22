from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()

# Список достижений
ACHIEVEMENTS = {
    'first_code': {
        'name': '🏆 Первый код',
        'description': 'Провел первый код-ревью',
        'points': 50,
        'icon': '🏆'
    },
    'leetcode_10': {
        'name': '📊 Новичок LeetCode',
        'description': 'Решил 10 задач',
        'points': 100,
        'icon': '📊'
    },
    'leetcode_50': {
        'name': '⭐ Серебряный кодер',
        'description': 'Решил 50 задач',
        'points': 500,
        'icon': '⭐'
    },
    'leetcode_100': {
        'name': '🏅 Золотой кодер',
        'description': 'Решил 100 задач',
        'points': 1000,
        'icon': '🏅'
    },
    'pomodoro_10': {
        'name': '🍅 Фокусник',
        'description': 'Провел 10 Pomodoro сессий',
        'points': 150,
        'icon': '🍅'
    },
    'pomodoro_50': {
        'name': '🔥 Мастер фокуса',
        'description': 'Провел 50 Pomodoro сессий',
        'points': 500,
        'icon': '🔥'
    },
    'first_project': {
        'name': '💡 Идейный вдохновитель',
        'description': 'Добавил первую идею проекта',
        'points': 30,
        'icon': '💡'
    },
    'first_interview': {
        'name': '🎯 Первое собеседование',
        'description': 'Записал первое собеседование',
        'points': 100,
        'icon': '🎯'
    },
    'perfect_code': {
        'name': '✨ Чистый код',
        'description': 'Получил 90+ баллов на код-ревью',
        'points': 200,
        'icon': '✨'
    },
    'streak_7': {
        'name': '⚡ 7-дневная серия',
        'description': 'Решал задачи 7 дней подряд',
        'points': 300,
        'icon': '⚡'
    }
}


@router.message(F.text == "🎖️ Достижения")
async def cmd_achievements(message: Message):
    """Показать достижения пользователя"""
    # Получаем достижения пользователя
    query = """
        SELECT a.*, ua.earned_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = %s
        WHERE a.is_active = TRUE
        ORDER BY a.required_points ASC
    """
    all_achievements = await db.fetch_all(query, (message.from_user.id,))

    # Получаем общую статистику
    query = """
        SELECT SUM(points) as total_points
        FROM user_points
        WHERE user_id = %s
    """
    points = await db.fetch_one(query, (message.from_user.id,))

    text = "🎖️ *Ваши достижения*\n\n"
    text += f"🏆 *Всего очков:* {points['total_points'] or 0}\n\n"

    # Показываем достижения
    for ach in all_achievements:
        if ach.get('earned_at'):
            text += f"✅ {ach['icon']} *{ach['name']}* - получено\n"
            text += f"   {ach['description']} (+{ach['points']} очков)\n\n"
        else:
            text += f"🔒 {ach['icon']} *{ach['name']}*\n"
            text += f"   {ach['description']}\n\n"

    # Прогресс до следующего уровня
    query = """
        SELECT COUNT(*) as solved_tasks
        FROM daily_tasks
        WHERE user_id = %s AND solved = TRUE
    """
    solved = await db.fetch_one(query, (message.from_user.id,))

    text += "\n📊 *Прогресс:*\n"
    text += f"• Решено задач: {solved['solved_tasks'] or 0}\n"
    text += f"• До следующего уровня: {50 - (solved['solved_tasks'] or 0)} задач"

    await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: CallbackQuery):
    """Показать таблицу лидеров"""
    query = """
        SELECT u.user_id, u.first_name, COALESCE(SUM(up.points), 0) as total_points
        FROM users u
        LEFT JOIN user_points up ON u.user_id = up.user_id
        GROUP BY u.user_id, u.first_name
        ORDER BY total_points DESC
        LIMIT 10
    """
    leaders = await db.fetch_all(query)

    text = "🏆 *Таблица лидеров*\n\n"
    for i, leader in enumerate(leaders, 1):
        medal = get_medal_emoji(i)
        text += f"{medal} *{leader['first_name'] or 'Аноним'}* - {leader['total_points']} очков\n"

    await callback.message.edit_text(text, parse_mode="Markdown")


async def check_achievements(user_id: int):
    """Проверка и выдача достижений"""
    # Проверяем количество решенных задач
    query = """
        SELECT COUNT(*) as solved
        FROM daily_tasks
        WHERE user_id = %s AND solved = TRUE
    """
    solved = await db.fetch_one(query, (user_id,))

    achievements_to_grant = []

    if solved['solved'] >= 10:
        achievements_to_grant.append('leetcode_10')
    if solved['solved'] >= 50:
        achievements_to_grant.append('leetcode_50')
    if solved['solved'] >= 100:
        achievements_to_grant.append('leetcode_100')

    # Проверяем Pomodoro сессии
    query = """
        SELECT COUNT(*) as sessions
        FROM pomodoro_sessions
        WHERE user_id = %s AND status = 'completed'
    """
    sessions = await db.fetch_one(query, (user_id,))

    if sessions['sessions'] >= 10:
        achievements_to_grant.append('pomodoro_10')
    if sessions['sessions'] >= 50:
        achievements_to_grant.append('pomodoro_50')

    # Выдаем достижения
    for ach_key in achievements_to_grant:
        await grant_achievement(user_id, ach_key)


async def grant_achievement(user_id: int, achievement_key: str):
    """Выдача достижения пользователю"""
    ach = ACHIEVEMENTS.get(achievement_key)
    if not ach:
        return

    # Проверяем, нет ли уже
    query = """
        SELECT id FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.id
        WHERE ua.user_id = %s AND a.key = %s
    """
    existing = await db.fetch_one(query, (user_id, achievement_key))

    if existing:
        return

    # Находим ID достижения
    query = "SELECT id FROM achievements WHERE key = %s"
    ach_id = await db.fetch_one(query, (achievement_key,))

    if ach_id:
        # Выдаем достижение
        query = """
            INSERT INTO user_achievements (user_id, achievement_id, earned_at)
            VALUES (%s, %s, NOW())
        """
        await db.execute(query, (user_id, ach_id['id']))

        # Начисляем очки
        await add_points(user_id, ach['points'], f"Достижение: {ach['name']}")


def get_medal_emoji(position: int) -> str:
    """Эмодзи медали"""
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    else:
        return f"{position}."


async def add_points(user_id: int, points: int, reason: str):
    """Добавление очков пользователю"""
    query = """
        INSERT INTO user_points (user_id, points, reason, earned_at)
        VALUES (%s, %s, %s, NOW())
    """
    await db.execute(query, (user_id, points, reason))