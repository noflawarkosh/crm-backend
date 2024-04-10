from fastapi import Request, HTTPException
from fastapi import Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import HASHSALT
from hashlib import pbkdf2_hmac
import random
import string

from auth.models import UserSessionModel, UserModel
from database import get_async_session


def hash_password(pwd: str) -> str:
    return pbkdf2_hmac('sha256', pwd.encode(), HASHSALT.encode(), 100000).hex()


def generate_token(length: int) -> str:
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_characters) for _ in range(length))


async def get_user(session, request):
    csrf = request.cookies.get('csrf_')
    result = None

    if csrf:
        query = select(UserSessionModel).where(and_(UserSessionModel.token == csrf, UserSessionModel.is_active))
        db_response = await session.execute(query)
        result = db_response.scalars().all()

        if result:
            user_session = result[0]
            query = select(UserModel).where(UserModel.id == user_session.user_id)
            db_response = await session.execute(query)
            result = db_response.scalars().all()

    return result[0] if result else None


async def any(session: AsyncSession = Depends(get_async_session), request: Request = Request):
    return await get_user(session, request)


async def authed(session: AsyncSession = Depends(get_async_session), request: Request = Request):
    result = await get_user(session, request)

    if result:
        return result
    else:
        raise HTTPException(status_code=401, detail="Не авторизован")


async def not_authed(session: AsyncSession = Depends(get_async_session), request: Request = Request):
    result = await get_user(session, request)

    if result:
        raise HTTPException(status_code=409, detail="Уже авторизован")
    else:
        return result
