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
    POMODORO_WORK_TIME = 25  # минут
    POMODORO_BREAK_TIME = 5  # минут

    # Настройки повторения ошибок
    ERROR_REVIEW_INTERVALS = [1, 3, 7, 14, 30]  # дни для повторения


config = Config()