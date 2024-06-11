from sqlalchemy import select, update, and_

from auth.models import (
    UserModel,
    UserStatusHistoryModel,
    UserSessionModel
)

from database import async_session_factory


class AuthRepository:

    @classmethod
    async def create_user(cls, data: dict) -> UserModel:
        try:
            async with async_session_factory() as session:

                user = UserModel(**data)
                session.add(user)
                await session.flush()

                user_status = UserStatusHistoryModel(user_id=user.id, status_id=1)
                session.add(user_status)
                await session.commit()

                await session.refresh(user)
                return user

        finally:
            await session.close()

    @classmethod
    async def read_user(cls, field: str, value) -> UserModel | None:
        try:

            async with async_session_factory() as session:

                query = (
                    select(UserModel)
                    .where(getattr(UserModel, field) == value)
                )

                db_response = await session.execute(query)
                user = db_response.unique().scalars().one_or_none()

                return user

        finally:
            await session.close()

    @classmethod
    async def update_user(cls, user_id: int, values: dict):
        try:
            async with async_session_factory() as session:

                query = (
                    update(UserModel)
                    .where(UserModel.id == user_id)
                    .values(**values)
                )

                await session.execute(query)
                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def create_session(cls, data: dict) -> UserSessionModel:
        try:
            async with async_session_factory() as session:

                user_session = UserSessionModel(**data)
                session.add(user_session)
                await session.commit()

                await session.refresh(user_session)
                return user_session

        finally:
            await session.close()

    @classmethod
    async def read_session(cls, token: str) -> UserSessionModel | None:
        try:
            async with async_session_factory() as session:

                query = (
                    select(UserSessionModel)
                    .where(
                        and_(
                            UserSessionModel.token == token,
                            UserSessionModel.is_active
                        )
                    )
                )

                db_response = await session.execute(query)

                user_session = db_response.unique().scalars().one_or_none()
                return user_session

        finally:
            await session.close()

    @classmethod
    async def disable_session(cls, token: str):
        try:
            async with async_session_factory() as session:

                query = (
                    update(UserSessionModel)
                    .where(UserSessionModel.token == token)
                    .values(is_active=False)
                )

                await session.execute(query)
                await session.commit()

        finally:
            await session.close()
