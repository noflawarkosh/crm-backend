from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from auth.models import UserModel
from auth.schemas import UserSchema

from auth.utils import hash_password

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.get('/test')
async def test():
    return 'test'


@router.post('/register')
async def register(user: Annotated[UserSchema, Depends()], session: AsyncSession = Depends(get_async_session)):

    user_dict = user.model_dump()
    print(user_dict)
    #user_dict['password'] = hash_password(user_dict['password'])

    #user_orm = UserModel(**user_dict)
    #session.add(user_orm)
    #await session.flush()

    #user_id = user_orm.id

    #await session.commit()

    return 'OK'