from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from sqlalchemy import func

from database import DefaultRepository
from strings import *
from auth.models import UserModel, UserSessionModel
from auth.repository import AuthRepository
from auth.schemas import (
    UserReadSchema,
    UserCreateSchema,
)
from auth.utils import (
    hash_password,
    generate_token
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


async def every(request: Request = Request):
    token = request.cookies.get(cookies_token_key)

    if not token:
        return None

    session = await AuthRepository.read_session(token)

    if session:
        if session.user.status_id != 2:
            return None

    return session


async def authed(request: Request = Request):
    session = await every(request)

    if session:
        return session

    raise HTTPException(status_code=401)


async def not_authed(request: Request = Request):
    if await every(request):
        raise HTTPException(status_code=409)


@router.post('/register')
async def register(data: Annotated[UserCreateSchema, Depends()], session: UserSessionModel = Depends(not_authed)):
    unique_fields = [
        ('email', data.email, string_user_email_exist),
        ('username', data.username, string_user_username_exist),
        ('telnum', data.telnum, string_user_telnum_exist),
        ('telegram', data.telegram, string_user_telegram_exist),
    ]

    for field, value, error in unique_fields:
        user_check = await DefaultRepository.get_records(
            UserModel,
            filters=[getattr(UserModel, field) == value]
        )
        if user_check:
            raise HTTPException(status_code=409, detail=error)

    data.password = hash_password(data.password)

    await DefaultRepository.save_records([{'model': UserModel, 'records': [{**data.model_dump(), 'status_id': 1}]}])


@router.post('/login')
async def login(request: Request, response: Response, username: str, password: str,
                session: UserSessionModel = Depends(not_authed)):
    user_check = await DefaultRepository.get_records(
        UserModel,
        filters=[UserModel.username == username.lower().replace(' ', '')]
    )

    if len(user_check) != 1:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    user_check = user_check[0]

    if hash_password(password) != user_check.password:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if user_check.status_id != 2:
        raise HTTPException(status_code=403, detail=string_user_inactive_user)

    user_session = await AuthRepository.create_session(
        {
            'user_id': user_check.id,
            'token': generate_token(128),
            'useragent': request.headers.get('user-agent'),
            'ip': request.client.host,
        }
    )

    response.set_cookie(key=cookies_token_key, value=user_session.token)


@router.get('/logout')
async def logout(request: Request, response: Response, session: UserSessionModel = Depends(authed)):
    await DefaultRepository.save_records(
        [{'model': UserSessionModel, 'records': [{'id': session.id, 'expires': func.now()}]}])
    response.delete_cookie(cookies_token_key)


@router.get('/myProfile')
async def get_self_user_profile(session: UserSessionModel = Depends(authed)) -> UserReadSchema:
    return UserReadSchema.model_validate(session.user, from_attributes=True)
