from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr

# User
from storage.schemas import StorageGETSchema


class UserCreateSchema(BaseModel):
    name: constr(max_length=100)
    username: constr(min_length=5, max_length=20)
    email: constr(max_length=100)
    telnum: constr(min_length=10, max_length=10)
    telegram: constr(max_length=50)
    password: constr(min_length=8, max_length=16)


class UserReadSchema(BaseModel):
    id: int
    name: str
    username: str
    email: str
    telnum: str
    telegram: str
    media_id: int | None


class UserReadFullSchema(UserReadSchema):
    media: StorageGETSchema | None
    statuses: list['UserStatusHistoryReadFullSchema']


class UserUpdateSchema(BaseModel):
    name: Optional[constr(max_length=100)] = None
    email: Optional[constr(max_length=100)] = None
    telnum: Optional[constr(min_length=10, max_length=10)] = None
    telegram: Optional[constr(max_length=50)] = None
    password: Optional[constr(min_length=8, max_length=16)] = None


# Session
class UserSessionCreateSchema(BaseModel):
    token: str
    useragent: str
    ip: str
    is_active: bool

    user_id: int


class UserSessionReadSchema(UserSessionCreateSchema):
    id: int
    user: UserReadFullSchema


# Status
class UserStatusReadSchema(BaseModel):
    id: int
    title: str


class UserStatusHistoryCreateSchema(BaseModel):
    description: str | None
    user_id: int
    status_id: int


class UserStatusHistoryReadSchema(UserStatusHistoryCreateSchema):
    id: int
    date: datetime


class UserStatusHistoryReadFullSchema(UserStatusHistoryReadSchema):
    status: UserStatusReadSchema
