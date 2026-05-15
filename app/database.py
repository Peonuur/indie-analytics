from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

# Получаем настройки из .env
settings = get_settings()

# Создаём асинхронный движок SQLAlchemy
# asyncpg - это быстрый асинхронный драйвер для PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",  # Выводить SQL-запросы в консоль (для отладки)
    pool_size=10,              # Количество постоянных соединений в пуле
    max_overflow=20,           # Максимальное количество дополнительных соединений
    pool_pre_ping=True         # Проверять соединение перед использованием (защита от обрывов)
)

# Создаём фабрику сессий
# AsyncSession - это асинхронная сессия для работы с БД
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Не сбрасывать объекты после commit (оптимизация)
)
