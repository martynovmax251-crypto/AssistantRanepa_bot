from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
import logging
from datetime import datetime
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class LeetCodeStates(StatesGroup):
    waiting_for_task = State()
    waiting_for_solution = State()


# База задач
TASKS = {
    'easy': [
        {'id': 1, 'title': 'Two Sum', 'description': 'Найти два числа, сумма которых равна target',
         'difficulty': 'easy'},
        {'id': 9, 'title': 'Palindrome Number', 'description': 'Проверить, является ли число палиндромом',
         'difficulty': 'easy'},
        {'id': 20, 'title': 'Valid Parentheses', 'description': 'Проверить правильность скобочной последовательности',
         'difficulty': 'easy'},
        {'id': 21, 'title': 'Merge Two Sorted Lists', 'description': 'Объединить два отсортированных списка',
         'difficulty': 'easy'},
        {'id': 53, 'title': 'Maximum Subarray', 'description': 'Найти подмассив с максимальной суммой',
         'difficulty': 'easy'},
    ],
    'medium': [
        {'id': 3, 'title': 'Longest Substring Without Repeating Characters',
         'description': 'Найти самую длинную подстроку без повторяющихся символов', 'difficulty': 'medium'},
        {'id': 15, 'title': '3Sum', 'description': 'Найти все тройки чисел, сумма которых равна 0',
         'difficulty': 'medium'},
        {'id': 33, 'title': 'Search in Rotated Sorted Array',
         'description': 'Поиск в повернутом отсортированном массиве', 'difficulty': 'medium'},
        {'id': 46, 'title': 'Permutations', 'description': 'Сгенерировать все перестановки массива',
         'difficulty': 'medium'},
        {'id': 55, 'title': 'Jump Game', 'description': 'Определить, можно ли достичь конца массива',
         'difficulty': 'medium'},
    ],
    'hard': [
        {'id': 4, 'title': 'Median of Two Sorted Arrays', 'description': 'Найти медиану двух отсортированных массивов',
         'difficulty': 'hard'},
        {'id': 10, 'title': 'Regular Expression Matching',
         'description': 'Реализовать сопоставление регулярных выражений', 'difficulty': 'hard'},
        {'id': 23, 'title': 'Merge k Sorted Lists', 'description': 'Объединить k отсортированных списков',
         'difficulty': 'hard'},
        {'id': 42, 'title': 'Trapping Rain Water', 'description': 'Вычислить количество воды после дождя',
         'difficulty': 'hard'},
    ]
}


async def get_user_level(user_id: int) -> str:
    """Получение уровня пользователя на основе решенных задач"""
    try:
        query = """
            SELECT COUNT(*) as solved
            FROM daily_tasks
            WHERE user_id = %s AND solved = TRUE
        """
        result = await db.fetch_one(query, (user_id,))
        solved_count = result['solved'] if result else 0

        if solved_count < 10:
            return 'easy'
        elif solved_count < 30:
            return random.choice(['easy', 'medium'])
        elif solved_count < 60:
            return random.choice(['medium', 'hard'])
        else:
            return random.choice(['medium', 'hard'])
    except Exception as e:
        logger.error(f"Ошибка при определении уровня пользователя: {e}")
        return random.choice(['easy', 'medium'])


def get_task_by_id(task_id: int):
    """Получить задачу по ID"""
    for difficulty in TASKS.values():
        for task in difficulty:
            if task['id'] == task_id:
                return task
    return None


def get_difficulty_emoji(difficulty: str) -> str:
    """Эмодзи сложности"""
    return {
        'easy': '🟢',
        'medium': '🟡',
        'hard': '🔴'
    }.get(difficulty, '⚪')


@router.message(F.text == "📊 LeetCode Tracker")
async def cmd_leetcode(message: Message):
    """Меню LeetCode трекера"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Ежедневная задача", callback_data="daily_task")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="leetcode_stats")],
        [InlineKeyboardButton(text="🏆 Челленджи", callback_data="challenges")],
        [InlineKeyboardButton(text="📝 Добавить решение", callback_data="add_solution")],
        [InlineKeyboardButton(text="🎯 Рандомная задача", callback_data="random_task")]
    ])

    await message.answer(
        "📊 *LeetCode Tracker*\n\n"
        "Отслеживайте прогресс решения задач!\n\n"
        "• Ежедневная задача — новая задача каждый день\n"
        "• Челленджи — соревнуйтесь с друзьями\n"
        "• Статистика — следите за своим прогрессом",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "daily_task")
async def get_daily_task(callback: CallbackQuery):
    """Получение ежедневной задачи"""
    try:
        # Проверяем, была ли сегодня задача
        query = """
            SELECT task_id, solved FROM daily_tasks 
            WHERE user_id = %s AND DATE(assigned_date) = CURDATE()
        """
        existing = await db.fetch_one(query, (callback.from_user.id,))

        if existing:
            if existing['solved']:
                await callback.message.edit_text(
                    "✅ Вы уже решили сегодняшнюю задачу!\n"
                    "Возвращайтесь завтра за новой!"
                )
            else:
                task = get_task_by_id(existing['task_id'])
                if task:
                    await callback.message.edit_text(
                        f"📅 *Ежедневная задача*\n\n"
                        f"*{task['title']}*\n\n"
                        f"{task['description']}\n\n"
                        f"Сложность: {get_difficulty_emoji(task['difficulty'])} {task['difficulty'].upper()}\n\n"
                        f"Отправьте /solve, чтобы добавить решение.",
                        parse_mode="Markdown"
                    )
            return

        # Выбираем новую задачу
        difficulty = await get_user_level(callback.from_user.id)
        task = random.choice(TASKS[difficulty])

        # Сохраняем в БД
        query = """
            INSERT INTO daily_tasks (user_id, task_id, task_title, difficulty, assigned_date)
            VALUES (%s, %s, %s, %s, CURDATE())
        """
        await db.execute(query, (callback.from_user.id, task['id'], task['title'], difficulty))

        await callback.message.edit_text(
            f"📅 *Ежедневная задача*\n\n"
            f"*{task['title']}*\n\n"
            f"{task['description']}\n\n"
            f"Сложность: {get_difficulty_emoji(difficulty)} {difficulty.upper()}\n\n"
            f"Отправьте /solve, чтобы добавить решение.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении ежедневной задачи: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )


@router.callback_query(F.data == "random_task")
async def random_task(callback: CallbackQuery):
    """Рандомная задача"""
    try:
        difficulty = random.choice(['easy', 'medium', 'hard'])
        task = random.choice(TASKS[difficulty])

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Решил", callback_data=f"mark_solved_{task['id']}")],
            [InlineKeyboardButton(text="🔄 Другую", callback_data="random_task")]
        ])

        await callback.message.edit_text(
            f"🎯 *Рандомная задача*\n\n"
            f"*{task['title']}*\n\n"
            f"{task['description']}\n\n"
            f"Сложность: {get_difficulty_emoji(difficulty)} {difficulty.upper()}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при получении рандомной задачи: {e}")
        await callback.message.edit_text("❌ Произошла ошибка. Попробуйте позже.")


@router.message(F.text == "/solve")
async def add_solution(message: Message, state: FSMContext):
    """Добавление решения"""
    await message.answer(
        "Отправьте ссылку на ваше решение (GitHub Gist, LeetCode решение) "
        "или опишите подход:"
    )
    await state.set_state(LeetCodeStates.waiting_for_solution)


@router.message(LeetCodeStates.waiting_for_solution)
async def process_solution(message: Message, state: FSMContext):
    """Сохранение решения"""
    try:
        solution = message.text

        # Обновляем задачу
        query = """
            UPDATE daily_tasks 
            SET solved = TRUE, solution_link = %s, solved_at = NOW()
            WHERE user_id = %s AND solved = FALSE
            ORDER BY assigned_date DESC LIMIT 1
        """
        await db.execute(query, (solution, message.from_user.id))

        # Начисляем очки
        points = 10

        # Сохраняем очки
        query_points = """
            INSERT INTO user_points (user_id, points, reason, earned_at)
            VALUES (%s, %s, %s, NOW())
        """
        await db.execute(query_points, (message.from_user.id, points, "Решение задачи LeetCode"))

        await message.answer(
            f"✅ Отлично! Решение сохранено.\n"
            f"Вы получили +{points} очков!\n\n"
            f"Продолжайте в том же духе!"
        )
    except Exception as e:
        logger.error(f"Ошибка при сохранении решения: {e}")
        await message.answer("❌ Произошла ошибка при сохранении решения.")
    finally:
        await state.clear()


@router.callback_query(F.data == "leetcode_stats")
async def show_leetcode_stats(callback: CallbackQuery):
    """Показать статистику"""
    try:
        query = """
            SELECT 
                difficulty,
                COUNT(*) as total,
                SUM(CASE WHEN solved = TRUE THEN 1 ELSE 0 END) as solved
            FROM daily_tasks
            WHERE user_id = %s
            GROUP BY difficulty
        """
        stats = await db.fetch_all(query, (callback.from_user.id,))

        query2 = """
            SELECT COUNT(*) as solved_today
            FROM daily_tasks
            WHERE user_id = %s AND solved = TRUE AND DATE(solved_at) = CURDATE()
        """
        today = await db.fetch_one(query2, (callback.from_user.id,))

        query3 = """
            SELECT SUM(points) as total_points
            FROM user_points
            WHERE user_id = %s
        """
        points = await db.fetch_one(query3, (callback.from_user.id,))

        text = "📊 *Ваша статистика LeetCode*\n\n"
        text += f"🏆 *Всего очков:* {points['total_points'] or 0}\n"
        text += f"✅ *Сегодня:* {today['solved_today'] or 0} задач\n\n"
        text += "*По сложности:*\n"

        if stats:
            for stat in stats:
                emoji = get_difficulty_emoji(stat['difficulty'])
                text += f"{emoji} {stat['difficulty'].upper()}: {stat['solved']}/{stat['total']}\n"
        else:
            text += "Пока нет решенных задач\n"

        text += "\nПродолжайте решать задачи каждый день!"

        await callback.message.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при получении статистики.")


@router.callback_query(F.data == "add_solution")
async def add_solution_callback(callback: CallbackQuery, state: FSMContext):
    """Добавить решение через callback"""
    await callback.message.edit_text(
        "Отправьте ссылку на ваше решение (GitHub Gist, LeetCode решение) "
        "или опишите подход:"
    )
    await state.set_state(LeetCodeStates.waiting_for_solution)


@router.callback_query(F.data == "challenges")
async def show_challenges(callback: CallbackQuery):
    """Показать челленджи"""
    await callback.message.edit_text(
        "🏆 *Челленджи*\n\n"
        "Скоро здесь появятся групповые челленджи!\n\n"
        "Пока что вы можете:\n"
        "• Решать ежедневные задачи\n"
        "• Соревноваться с друзьями\n"
        "• Следить за таблицей лидеров\n\n"
        "Используйте /leaderboard для просмотра рейтинга.",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("mark_solved_"))
async def mark_task_solved(callback: CallbackQuery, state: FSMContext):
    """Отметить задачу как решенную"""
    try:
        task_id = int(callback.data.split("_")[2])

        # Сохраняем в БД
        query = """
            INSERT INTO daily_tasks (user_id, task_id, solved, solved_at)
            VALUES (%s, %s, TRUE, NOW())
            ON DUPLICATE KEY UPDATE
            solved = TRUE, solved_at = NOW()
        """
        await db.execute(query, (callback.from_user.id, task_id))

        # Начисляем очки
        points = 10
        query_points = """
            INSERT INTO user_points (user_id, points, reason, earned_at)
            VALUES (%s, %s, %s, NOW())
        """
        await db.execute(query_points, (callback.from_user.id, points, f"Решение задачи #{task_id}"))

        await callback.message.edit_text(
            f"✅ Отлично! Задача отмечена как решенная.\n"
            f"Вы получили +{points} очков!\n\n"
            f"Продолжайте в том же духе!"
        )
    except Exception as e:
        logger.error(f"Ошибка при отметке задачи: {e}")
        await callback.message.edit_text("❌ Произошла ошибка.")
    finally:
        await state.clear()