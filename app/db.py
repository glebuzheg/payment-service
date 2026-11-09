from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.settings import database_url


def now():
    return datetime.now(timezone.utc)


engine = create_async_engine(database_url())
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
