from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from auth.models import UserModel, UserStatusHistoryModel
from auth.schemas import UserSchema

from auth.utils import hash_password

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post('/register')
async def register(user: Annotated[UserSchema, Depends()], session: AsyncSession = Depends(get_async_session)):

    user_dict = user.model_dump()
    user_dict['email'] = user_dict['email'].lower()
    user_dict['username'] = user_dict['username'].lower()
    user_dict['password'] = hash_password(user_dict['password'])

    query = select(UserModel.email).where(UserModel.email == user.email)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанная почта уже используется'}

    query = select(UserModel.username).where(UserModel.username == user.username)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный логин уже используется'}

    query = select(UserModel.telnum).where(UserModel.telnum == user.telnum)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный телефон уже используется'}

    query = select(UserModel.telegram).where(UserModel.telegram == user.telegram)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный тег телеграмм уже используется'}

    user_orm = UserModel(**user_dict)
    session.add(user_orm)
    await session.flush()

    user_status = UserStatusHistoryModel(user_id=user_orm.id, status_id=1)
    session.add(user_status)

    await session.commit()

    return {'result': 'success'}

