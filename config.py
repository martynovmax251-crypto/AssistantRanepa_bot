import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'it_student_db')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    OCR_LANG = os.getenv('OCR_LANG', 'rus+eng')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Настройки Pomodoro
    POMODORO_WORK_TIME = int(os.getenv('POMODORO_WORK_TIME', 25))
    POMODORO_BREAK_TIME = int(os.getenv('POMODORO_BREAK_TIME', 5))

    # Настройки повторения ошибок
    ERROR_REVIEW_INTERVALS = [1, 3, 7, 14, 30]

    # Настройки LeetCode
    LEETCODE_API_URL = os.getenv('LEETCODE_API_URL', 'https://leetcode.com/graphql')

    # Настройки для Team Up
    MAX_TEAM_MEMBERS = int(os.getenv('MAX_TEAM_MEMBERS', 5))

    # Настройки для интервью
    INTERVIEW_QUESTIONS_PER_SESSION = int(os.getenv('INTERVIEW_QUESTIONS_PER_SESSION', 5))


config = Config()