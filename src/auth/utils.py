from config import HASHSALT
from hashlib import pbkdf2_hmac
import random
import string


def hash_password(pwd: str) -> str:
    return pbkdf2_hmac('sha256', pwd.encode(), HASHSALT.encode(), 100000).hex()


def generate_token(length: int) -> str:
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_characters) for _ in range(length))
