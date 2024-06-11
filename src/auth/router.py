from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException

from auth.repository import (
    AuthRepository
)

from auth.schemas import (
    UserReadSchema,
    UserCreateSchema,
    UserSessionCreateSchema,
    UserUpdateSchema,
    UserReadFullSchema,
    UserSessionReadSchema
)

from auth.utils import (
    hash_password,
    generate_token
)

from strings import *

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


async def get_session(request):
    token = request.cookies.get(cookies_token_key)

    if not token:
        return None

    return await AuthRepository.read_session(token)


async def every(request: Request = Request):
    session = await get_session(request)
    if session:
        if session.user.statuses[-1].status_id != 2:
            return None

    return session


async def authed(request: Request = Request):
    session = await get_session(request)

    if session:
        if session.user.statuses[-1].status_id != 2:
            raise HTTPException(status_code=403, detail=string_user_inactive_user)

        return UserSessionReadSchema.model_validate(session, from_attributes=True)

    raise HTTPException(status_code=401)


async def not_authed(request: Request = Request):
    session = await get_session(request)

    if session:
        if session.user.statuses[-1].status_id != 2:
            raise HTTPException(status_code=403, detail=string_user_inactive_user)

        raise HTTPException(status_code=409)


@router.post('/register')
async def register(data: Annotated[UserCreateSchema, Depends()],
                   session: UserSessionReadSchema = Depends(not_authed)
                   ) -> UserReadSchema:
    unique_fields = [
        ('email', data.email, string_user_email_exist),
        ('username', data.username, string_user_username_exist),
        ('telnum', data.telnum, string_user_telnum_exist),
        ('telegram', data.telegram, string_user_telegram_exist),
    ]

    for field, value, error in unique_fields:
        user_check = await AuthRepository.read_user(field, value.lower().replace(' ', ''))
        if user_check:
            raise HTTPException(status_code=409, detail=error)

    data.password = hash_password(data.password)
    new_user = await AuthRepository.create_user(data.model_dump())

    if not new_user:
        raise HTTPException(status_code=500, detail=string_user_register_error)

    return UserReadSchema.model_validate(new_user, from_attributes=True)


@router.post('/login')
async def login(request: Request,
                response: Response,
                username: str,
                password: str,
                session: UserSessionReadSchema = Depends(not_authed)
                ):
    user_check = await AuthRepository.read_user('username', username.lower().replace(' ', ''))
    if not user_check:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if hash_password(password) != user_check.password:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if user_check.statuses[-1].status_id != 2:
        raise HTTPException(status_code=403, detail=string_user_inactive_user)

    user_session = await AuthRepository.create_session(
        {
            'user_id': user_check.id,
            'token': generate_token(128),
            'useragent': request.headers.get('user-agent'),
            'ip': request.client.host,
            'is_active': True
        }
    )

    response.set_cookie(key=cookies_token_key, value=user_session.token)


@router.get('/logout')
async def logout(request: Request,
                 response: Response,
                 session: UserSessionReadSchema = Depends(authed)
                 ):
    await AuthRepository.disable_session(request.cookies.get(cookies_token_key))
    response.delete_cookie(cookies_token_key)


@router.get('/myProfile')
async def get_self_user_profile(session: UserSessionReadSchema = Depends(authed)) -> UserReadFullSchema:
    return UserReadFullSchema.model_validate(session.user, from_attributes=True)
