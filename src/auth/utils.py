from config import HASHSALT
from hashlib import pbkdf2_hmac


def hash_password(pwd):
    return pbkdf2_hmac('sha256', pwd.encode(), HASHSALT.encode(), 100000).hex()
