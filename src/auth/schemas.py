from typing import Optional
from pydantic import BaseModel, constr


class UserSchema(BaseModel):
    id: Optional[int] = None
    name: constr(max_length=100)
    username: constr(min_length=5, max_length=20)
    email: constr(max_length=100)
    telnum: constr(min_length=10, max_length=10)
    telegram: constr(max_length=50)
    password: constr(min_length=8, max_length=16)


class UserGETSchema(BaseModel):
    id: int
    name: constr(max_length=100)
    username: constr(min_length=5, max_length=20)
    email: constr(max_length=100)
    telnum: constr(min_length=10, max_length=10)
    telegram: constr(max_length=50)


class LoginSchema(BaseModel):
    username: constr(min_length=5, max_length=20)
    password: constr(min_length=8, max_length=16)


class UpdateProfileSchema(BaseModel):
    name: constr(max_length=100)
    email: constr(max_length=100)
    telnum: constr(min_length=10, max_length=10)
    telegram: constr(max_length=50)


class UserProfileSchema(BaseModel):
    id: Optional[int] = None
    name: constr(max_length=100)
    username: constr(min_length=5, max_length=20)
    email: constr(max_length=100)
    telnum: constr(min_length=10, max_length=10)
    telegram: constr(max_length=50)
