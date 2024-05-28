from auth.models import UserModel, UserStatusHistoryModel
from auth.schemas import UserPOSTSchema
from auth.utils import hash_password
from database import async_session_factory


class UserRepository:

    @classmethod
    async def register(cls, data: UserPOSTSchema) -> UserModel:

        try:

            async with async_session_factory() as session:

                data_dict = data.model_dump()
                data_dict['email'] = data_dict['email'].lower()
                data_dict['username'] = data_dict['username'].lower()
                data_dict['password'] = hash_password(data_dict['password'])

                user = UserModel(**data_dict)

                session.add(user)

                await session.flush()

                new_user_status = UserStatusHistoryModel(user_id=user.id, status_id=1)
                session.add(new_user_status)

                await session.commit()

                return user

        finally:
            await session.close()
