from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import ast
import logging
from database.db_config import db

logger = logging.getLogger(__name__)
router = Router()


class CodeReviewStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_language = State()


@router.message(F.text == "🔍 Код-ревью")
async def cmd_code_review(message: Message, state: FSMContext):
    """Начало код-ревью"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐍 Python", callback_data="lang_python")],
        [InlineKeyboardButton(text="📜 JavaScript", callback_data="lang_javascript")],
        [InlineKeyboardButton(text="☕ Java", callback_data="lang_java")],
        [InlineKeyboardButton(text="⚙️ C++", callback_data="lang_cpp")]
    ])

    await message.answer(
        "🔍 *Код-ревью помощник*\n\n"
        "Выберите язык программирования и отправьте код для анализа.\n"
        "Я проверю:\n"
        "• Синтаксические ошибки\n"
        "• Стиль кода\n"
        "• Потенциальные баги\n"
        "• Оптимизации",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(CodeReviewStates.waiting_for_language)


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    """Установка языка программирования"""
    language = callback.data.split("_")[1]
    await state.update_data(language=language)

    await callback.message.edit_text(
        f"✅ Выбран язык: *{language.upper()}*\n\n"
        f"Отправьте код для анализа:",
        parse_mode="Markdown"
    )
    await state.set_state(CodeReviewStates.waiting_for_code)


@router.message(CodeReviewStates.waiting_for_code)
async def analyze_code(message: Message, state: FSMContext):
    """Анализ присланного кода"""
    data = await state.get_data()
    language = data.get('language')
    code = message.text

    if not code:
        await message.answer("Пожалуйста, отправьте код текстом.")
        return

    # Отправляем сообщение о начале анализа
    loading_msg = await message.answer("🔍 *Анализирую код...*", parse_mode="Markdown")

    # Проводим анализ
    analysis = perform_code_review(code, language)

    # Формируем результат
    result = format_review_result(analysis, language)

    # Сохраняем в статистику
    await save_review_stats(message.from_user.id, analysis)

    # Удаляем сообщение о загрузке
    await loading_msg.delete()

    # Отправляем результат
    await message.answer(result, parse_mode="Markdown")
    await state.clear()


def perform_code_review(code: str, language: str) -> dict:
    """Выполнение анализа кода"""
    result = {
        'errors': [],
        'warnings': [],
        'suggestions': [],
        'score': 100,
        'complexity': 'Низкая'
    }

    if language == 'python':
        result = analyze_python_code(code)
    elif language == 'javascript':
        result = analyze_javascript_code(code)
    elif language == 'java':
        result = analyze_java_code(code)
    elif language == 'cpp':
        result = analyze_cpp_code(code)
    else:
        result['errors'].append("Язык не поддерживается")

    return result


def analyze_python_code(code: str) -> dict:
    """Анализ Python кода"""
    result = {'errors': [], 'warnings': [], 'suggestions': [], 'score': 100}

    try:
        # Синтаксический анализ
        tree = ast.parse(code)

        # Проверка на типичные ошибки
        for node in ast.walk(tree):
            # Проверка на слишком длинные функции
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 50:
                    result['warnings'].append(
                        f"Функция '{node.name}' слишком длинная ({len(node.body)} строк). "
                        "Рекомендуется разбить на более мелкие функции."
                    )
                    result['score'] -= 5

                # Проверка документации
                if not ast.get_docstring(node):
                    result['suggestions'].append(
                        f"Добавьте docstring для функции '{node.name}'"
                    )
                    result['score'] -= 2

            # Проверка на глобальные переменные
            if isinstance(node, ast.Global):
                result['warnings'].append(
                    "Использование глобальной переменной. "
                    "Рассмотрите альтернативные подходы."
                )
                result['score'] -= 3

            # Проверка на try-except без указания исключения
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                result['warnings'].append(
                    "Пустой except блок. Укажите конкретное исключение."
                )
                result['score'] -= 5

        # Проверка стиля
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 79:
                result['suggestions'].append(
                    f"Строка {i} длиннее 79 символов ({len(line)})."
                )
                result['score'] -= 1

            if line and not line[0].isspace() and line.strip() and not line.endswith(':'):
                if any(keyword in line for keyword in ['if', 'for', 'while', 'def', 'class']):
                    if not line.endswith(':'):
                        result['errors'].append(
                            f"Строка {i}: пропущено двоеточие в конце."
                        )
                        result['score'] -= 10

        # Проверка импортов
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        if len(imports) > 10:
            result['suggestions'].append(
                f"Много импортов ({len(imports)}). "
                "Сгруппируйте их или разбейте модуль."
            )
            result['score'] -= 3

        # Определение сложности
        function_count = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
        if function_count > 10:
            result['complexity'] = 'Высокая'
        elif function_count > 5:
            result['complexity'] = 'Средняя'
        else:
            result['complexity'] = 'Низкая'

    except SyntaxError as e:
        result['errors'].append(f"Синтаксическая ошибка: {e}")
        result['score'] = 0
    except Exception as e:
        result['errors'].append(f"Ошибка анализа: {e}")

    # Нормализуем оценку
    result['score'] = max(0, min(100, result['score']))

    return result


def analyze_javascript_code(code: str) -> dict:
    """Анализ JavaScript кода"""
    result = {'errors': [], 'warnings': [], 'suggestions': [], 'score': 100}

    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        # Проверка на var (использовать let/const)
        if 'var ' in line and not line.strip().startswith('//'):
            result['warnings'].append(
                f"Строка {i}: используйте 'let' или 'const' вместо 'var'"
            )
            result['score'] -= 3

        # Проверка на == (строгое сравнение)
        if '==' in line and '===' not in line and '!=' in line and '!==' not in line:
            if not line.strip().startswith('//'):
                result['suggestions'].append(
                    f"Строка {i}: используйте строгое сравнение (=== или !==)"
                )
                result['score'] -= 2

        # Проверка на отсутствие ;
        if line.strip() and not line.strip().endswith(';') and not line.strip().endswith(
                '{') and not line.strip().endswith('}'):
            if not line.strip().startswith('//') and not line.strip().startswith('/*'):
                result['suggestions'].append(
                    f"Строка {i}: рекомендуется ставить точку с запятой"
                )
                result['score'] -= 1

        # Проверка длины строки
        if len(line) > 80:
            result['suggestions'].append(
                f"Строка {i} длиннее 80 символов ({len(line)})."
            )
            result['score'] -= 1

    # Проверка на console.log в production
    if 'console.log' in code:
        result['warnings'].append(
            "Обнаружены console.log. Удалите их перед отправкой в production."
        )
        result['score'] -= 5

    # Проверка на асинхронность
    if 'callback' in code and 'async' not in code:
        result['suggestions'].append(
            "Рассмотрите использование async/await вместо callback."
        )
        result['score'] -= 2

    result['score'] = max(0, min(100, result['score']))
    result['complexity'] = 'Средняя' if len(lines) > 100 else 'Низкая'

    return result


def analyze_java_code(code: str) -> dict:
    """Анализ Java кода"""
    result = {'errors': [], 'warnings': [], 'suggestions': [], 'score': 100}

    # Проверка на имя класса
    if 'public class' in code:
        class_name_match = re.search(r'public class\s+(\w+)', code)
        if class_name_match:
            class_name = class_name_match.group(1)
            if not class_name[0].isupper():
                result['errors'].append(
                    f"Имя класса '{class_name}' должно начинаться с заглавной буквы"
                )
                result['score'] -= 10

    # Проверка на main метод
    if 'public static void main' in code:
        if 'String[] args' not in code:
            result['errors'].append("main метод должен иметь параметр String[] args")
            result['score'] -= 10

    # Проверка на System.out.println
    if 'System.out.println' in code:
        result['suggestions'].append(
            "Используйте логгер (Logger) вместо System.out.println"
        )
        result['score'] -= 2

    result['score'] = max(0, min(100, result['score']))
    result['complexity'] = 'Средняя' if len(code.split('\n')) > 150 else 'Низкая'

    return result


def analyze_cpp_code(code: str) -> dict:
    """Анализ C++ кода"""
    result = {'errors': [], 'warnings': [], 'suggestions': [], 'score': 100}

    # Проверка на using namespace std
    if 'using namespace std;' in code:
        result['warnings'].append(
            "Избегайте 'using namespace std;' в заголовочных файлах и больших проектах."
        )
        result['score'] -= 3

    # Проверка на умные указатели
    if 'new ' in code and 'delete' not in code:
        result['warnings'].append(
            "Обнаружены new без delete. Используйте умные указатели (unique_ptr, shared_ptr)."
        )
        result['score'] -= 5

    # Проверка на заголовочные файлы
    if '#include <iostream>' in code and '#include <string>' not in code:
        if 'string' in code:
            result['suggestions'].append(
                "Добавьте #include <string> для работы со строками."
            )
            result['score'] -= 2

    result['score'] = max(0, min(100, result['score']))
    result['complexity'] = 'Средняя' if len(code.split('\n')) > 120 else 'Низкая'

    return result


def format_review_result(analysis: dict, language: str) -> str:
    """Форматирование результата анализа"""
    result = f"🔍 *Результат код-ревью ({language.upper()})*\n\n"

    # Оценка
    score = analysis['score']
    if score >= 90:
        grade = "🏆 Отлично!"
    elif score >= 70:
        grade = "👍 Хорошо"
    elif score >= 50:
        grade = "⚠️ Требует доработки"
    else:
        grade = "❌ Критические ошибки"

    result += f"*Оценка:* {score}/100 {grade}\n"
    result += f"*Сложность:* {analysis['complexity']}\n\n"

    # Ошибки
    if analysis['errors']:
        result += "❌ *Ошибки:*\n"
        for error in analysis['errors'][:5]:
            result += f"• {error}\n"
        result += "\n"

    # Предупреждения
    if analysis['warnings']:
        result += "⚠️ *Предупреждения:*\n"
        for warning in analysis['warnings'][:5]:
            result += f"• {warning}\n"
        result += "\n"

    # Рекомендации
    if analysis['suggestions']:
        result += "💡 *Рекомендации:*\n"
        for suggestion in analysis['suggestions'][:5]:
            result += f"• {suggestion}\n"
        result += "\n"

    # Мотивация
    if score < 60:
        result += "📚 *Рекомендация:* Пройдите курсы по чистому коду и посмотрите примеры хороших проектов на GitHub."
    elif score < 80:
        result += "📚 *Рекомендация:* Обратите внимание на стиль кода и документацию."
    else:
        result += "🎉 *Отлично!* Код хорошего качества. Продолжайте в том же духе!"

    return result


async def save_review_stats(user_id: int, analysis: dict):
    """Сохранение статистики код-ревью"""
    try:
        query = """
            INSERT INTO code_review_stats (user_id, score, errors_count, warnings_count, reviewed_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        await db.execute(query, (
            user_id,
            analysis['score'],
            len(analysis['errors']),
            len(analysis['warnings'])
        ))

        # Если оценка выше 90, выдаем достижение "Чистый код"
        if analysis['score'] >= 90:
            await check_perfect_code_achievement(user_id)

    except Exception as e:
        logger.error(f"Ошибка при сохранении статистики код-ревью: {e}")


async def check_perfect_code_achievement(user_id: int):
    """Проверка и выдача достижения за чистый код"""
    try:
        query = """
            SELECT id FROM achievements WHERE `key` = 'perfect_code'
        """
        ach = await db.fetch_one(query)

        if ach:
            query_check = """
                SELECT id FROM user_achievements 
                WHERE user_id = %s AND achievement_id = %s
            """
            existing = await db.fetch_one(query_check, (user_id, ach['id']))

            if not existing:
                query_insert = """
                    INSERT INTO user_achievements (user_id, achievement_id, earned_at)
                    VALUES (%s, %s, NOW())
                """
                await db.execute(query_insert, (user_id, ach['id']))

                query_points = """
                    INSERT INTO user_points (user_id, points, reason, earned_at)
                    VALUES (%s, %s, %s, NOW())
                """
                await db.execute(query_points, (user_id, 200, "Достижение: Чистый код"))

    except Exception as e:
        logger.error(f"Ошибка при выдаче достижения: {e}")