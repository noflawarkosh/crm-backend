from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER


DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


async_engine = create_async_engine(url=DATABASE_URL)
async_session_factory = async_sessionmaker(async_engine)

async def check_field_is_unique(session, field, value):
    query = select(field).where(field == value)
    result = await session.execute(query)
    print(result)
    if len(result.all()) == 0:
        return True
    return False

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


class Base(DeclarativeBase):
    pass