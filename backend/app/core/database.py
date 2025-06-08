from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=NullPool,
    echo=settings.DEBUG,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create declarative base using modern SQLAlchemy 2.0 style


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)


# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
