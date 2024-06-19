from sqlalchemy import select, update, and_, func

from auth.models import (
    UserModel,
    UserSessionModel
)

from database import async_session_factory


class AuthRepository:

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
                            UserSessionModel.expires > func.now()
                        )
                    )
                )

                db_response = await session.execute(query)

                user_session = db_response.unique().scalars().one_or_none()
                return user_session

        finally:
            await session.close()
