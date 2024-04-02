from typing import Annotated

from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from auth.models import UserModel, UserStatusHistoryModel, UserSessionModel
from auth.schemas import UserSchema, LoginSchema

from auth.utils import hash_password, generate_token, get_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post('/register')
async def register(request: Request,
                   userform: Annotated[UserSchema, Depends()],
                   session: AsyncSession = Depends(get_async_session)):

    user = await get_user(session, request)
    if user:
        return {'result': 'error', 'details': 'Уже авторизован'}

    user_dict = userform.model_dump()
    user_dict['email'] = user_dict['email'].lower()
    user_dict['username'] = user_dict['username'].lower()
    user_dict['password'] = hash_password(user_dict['password'])

    query = select(UserModel.email).where(UserModel.email == userform.email)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанная почта уже используется'}

    query = select(UserModel.username).where(UserModel.username == userform.username)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный логин уже используется'}

    query = select(UserModel.telnum).where(UserModel.telnum == userform.telnum)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный телефон уже используется'}

    query = select(UserModel.telegram).where(UserModel.telegram == userform.telegram)
    result = await session.execute(query)
    if len(result.all()) != 0:
        return {'result': 'error', 'details': 'Указанный тег телеграмм уже используется'}

    user_orm = UserModel(**user_dict)
    session.add(user_orm)
    await session.flush()

    user_status = UserStatusHistoryModel(user_id=user_orm.id, status_id=1)
    session.add(user_status)

    await session.commit()

    return {'result': 'success', 'details': 'Успешная регистрация'}

@router.post('/login')
async def login(request: Request,
                response: Response,
                data: Annotated[LoginSchema, Depends()],
                session: AsyncSession = Depends(get_async_session)):

    user = await get_user(session, request)

    if user:
        return {'result': 'error', 'details': 'Уже авторизован'}

    query = select(UserModel).where(UserModel.username == data.username)
    db_response = await session.execute(query)
    result = db_response.scalars().all()

    if len(result) != 1:
        return {'result': 'error', 'details': 'Неверный пользователь или пароль'}

    user = result[0]

    if hash_password(data.password) != user.password:
        return {'result': 'error', 'details': 'Неверный пользователь или пароль'}

    query = select(UserStatusHistoryModel).where(UserStatusHistoryModel.user_id == user.id).order_by(UserStatusHistoryModel.id.desc())
    db_response = await session.execute(query)
    result = db_response.scalars().all()

    current_status = result[0]

    if current_status.status_id != 2:
        return {'result': 'error', 'details': 'Учетная запись не активна'}

    auth_token = generate_token(64)

    user_session_dict ={
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


@router.post('/logout')
async def logout(request: Request,
                response: Response,
                session: AsyncSession = Depends(get_async_session)):

    csrf = request.cookies.get('csrf_')
    if not csrf:
        return {'result': 'error', 'details': 'Токен клиента отстутствует в cookies'}
    print(csrf)
    query = update(UserSessionModel).where(UserSessionModel.token == csrf).values(is_active=False)
    await session.execute(query)
    await session.commit()

    response.delete_cookie('csrf_')
    return {'result': 'success', 'details': 'Успешное закрытие сессии пользователя'}

