from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.repository import UserRepository
from database import get_async_session, check_field_is_unique

from auth.models import UserModel, UserStatusHistoryModel, UserSessionModel
from auth.schemas import LoginSchema, UserProfileSchema, UpdateProfileSchema, UserGETSchema, UserPOSTSchema
from auth.utils import hash_password, generate_token, any, authed, not_authed
from strings import *

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post('/register')
async def register(data: Annotated[UserPOSTSchema, Depends()],
                   user: UserModel = Depends(not_authed)
                   ) -> UserGETSchema:

    data_dict = data.model_dump()
    data_dict['email'] = data_dict['email'].lower()
    data_dict['username'] = data_dict['username'].lower()

    if not await check_field_is_unique(UserModel.email, data_dict['email']):
        raise HTTPException(status_code=409, detail=string_user_email_exist)

    if not await check_field_is_unique(UserModel.username, data_dict['username']):
        raise HTTPException(status_code=409, detail=string_user_username_exist)

    if not await check_field_is_unique(UserModel.telnum, data_dict['telnum']):
        raise HTTPException(status_code=409, detail=string_user_telnum_exist)

    if not await check_field_is_unique(UserModel.telegram, data_dict['telegram']):
        raise HTTPException(status_code=409, detail=string_user_telegram_exist)

    new_user = await UserRepository.register(data)
    dto = UserGETSchema.model_validate(new_user, from_attributes=True)

    return dto


@router.post('/login')
async def login(request: Request,
                response: Response,
                data: Annotated[LoginSchema, Depends()],
                user: UserModel = Depends(not_authed),
                session: AsyncSession = Depends(get_async_session)):

    query = select(UserModel).where(UserModel.username == data.username.lower())
    db_response = await session.execute(query)
    result = db_response.scalars().all()

    if len(result) != 1:
        return {'result': 'error', 'details': 'Неверный пользователь или пароль'}

    user = result[0]

    if hash_password(data.password) != user.password:
        return {'result': 'error', 'details': 'Неверный пользователь или пароль'}

    query = select(UserStatusHistoryModel).where(UserStatusHistoryModel.user_id == user.id).order_by(
        UserStatusHistoryModel.id.desc())
    db_response = await session.execute(query)
    result = db_response.scalars().all()

    current_status = result[0]

    if current_status.status_id != 2:
        return {'result': 'error', 'details': 'Учетная запись не активна'}

    auth_token = generate_token(64)

    user_session_dict = {
        'user_id': user.id,
        'token': auth_token,
        'useragent': request.headers.get('user-agent'),
        'ip': request.client.host,
        'is_active': True
    }
    user_session = UserSessionModel(**user_session_dict)
    session.add(user_session)
    await session.commit()

    response.set_cookie(key='csrf_', value=auth_token)
    return {'result': 'success', 'details': 'Успешная авторизация'}


@router.get('/logout')
async def logout(request: Request,
                 response: Response,
                 session: AsyncSession = Depends(get_async_session)):
    csrf = request.cookies.get('csrf_')
    if not csrf:
        return {'result': 'error', 'details': 'Токен клиента отстутствует в cookies'}
    query = update(UserSessionModel).where(UserSessionModel.token == csrf).values(is_active=False)
    await session.execute(query)
    await session.commit()

    response.delete_cookie('csrf_')
    return {'result': 'success', 'details': 'Успешное закрытие сессии пользователя'}


@router.post('/updateSelfProfile')
async def update_self_user_profile(request: Request,
                                   response: Response,
                                   data: Annotated[UpdateProfileSchema, Depends()],
                                   user: UserModel = Depends(authed),
                                   session: AsyncSession = Depends(get_async_session)):

    user.telnum = data.telnum
    user.email = data.email
    user.name = data.name
    user.telegram = data.telegram

    await session.commit()
    return {'result': 'success', 'details': 'Успешное обновление данных пользователя'}

@router.get('/getSelfProfile')
async def get_self_user_profile(request: Request,
                                response: Response,
                                user: UserModel = Depends(authed),
                                session: AsyncSession = Depends(get_async_session)) -> UserProfileSchema:
    return UserProfileSchema.model_validate(user.__dict__)
