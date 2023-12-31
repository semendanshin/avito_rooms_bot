from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from database.types import UserCreate
from database.enums import UserRole
from typing import Optional


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    result = await session.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    return user


async def create_user(session: AsyncSession, user: UserCreate) -> User:
    if await get_user(session, user.id):
        raise ValueError('This user already exists')

    user = User(**user.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_role(session: AsyncSession, username: str, role: UserRole) -> User:
    await session.execute(update(User).where(User.username == username).values(role=role))
    await session.commit()
    return await get_user_by_username(session, username)


async def get_admins(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).filter(User.role == UserRole.ADMIN))
    return list(result.scalars().all())


async def get_dispatchers(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).filter(User.role == UserRole.DISPATCHER))
    return list(result.scalars().all())
