import os

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


SqlAlchemyBase = declarative_base()

engine = None
session_factory = None


async def global_init():
    global engine, session_factory

    if session_factory:
        return

    url_connection = os.getenv('DATABASE_URL')

    print(f"Connection to {url_connection}")

    engine = create_async_engine(url_connection, echo=False)
    session_factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    from . import __all_models

    async with engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


async def create_session():
    global session_factory
    async with session_factory() as session:
        yield session
