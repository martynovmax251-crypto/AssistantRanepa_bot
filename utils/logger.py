import logging
import sys
from pathlib import Path
from config import config


def setup_logger():
    """Настройка логирования"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Создаем папку для логов если её нет
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Настройка корневого логгера
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_dir / 'bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


logger = setup_logger()