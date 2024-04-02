from sqlalchemy import select, and_
from config import HASHSALT
from hashlib import pbkdf2_hmac
import random
import string

from auth.models import UserSessionModel, UserModel

def hash_password(pwd: str) -> str:
    return pbkdf2_hmac('sha256', pwd.encode(), HASHSALT.encode(), 100000).hex()


def generate_token(length: int) -> str:
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_characters) for _ in range(length))


async def get_user(session, request):

    csrf = request.cookies.get('csrf_')
    if csrf:
        query = select(UserSessionModel).where(and_(UserSessionModel.token == csrf, UserSessionModel.is_active))
        db_response = await session.execute(query)
        result = db_response.scalars().all()

        if result:
            user_session = result[0]
            query = select(UserModel).where(UserModel.id == user_session.user_id)
            db_response = await session.execute(query)
            result = db_response.scalars().all()
            if result:
                return result[0]

        return None


