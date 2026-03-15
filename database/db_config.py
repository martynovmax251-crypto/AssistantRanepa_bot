import aiomysql
from typing import Optional
import logging
from config import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self):
        """Создание пула соединений с БД"""
        try:
            self.pool = await aiomysql.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
                charset='utf8mb4',
                autocommit=True
            )
            logger.info("Подключение к БД успешно установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise

    async def execute(self, query: str, params: tuple = None):
        """Выполнение SQL запроса"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return cursor

    async def fetch_one(self, query: str, params: tuple = None):
        """Получение одной записи"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple = None):
        """Получение всех записей"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                return await cursor.fetchall()

    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Соединение с БД закрыто")


# Создаем экземпляр класса Database
db = Database()