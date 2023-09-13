import os

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession

from database.entities import Base

engine: AsyncEngine = create_async_engine(
    os.getenv('DB_CONNECTION_STRING'),
    echo=True
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def get_wolrus_connection():
    return await asyncpg.connect(
        host=os.getenv('WOL_DB_HOST'),
        database=os.getenv('WOL_DB_NAME'),
        user=os.getenv('WOL_DB_USER'),
        password=os.getenv('WOL_DB_PASSWORD'),
        port=os.getenv('WOL_DB_PORT')
    )


async def database_init() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
