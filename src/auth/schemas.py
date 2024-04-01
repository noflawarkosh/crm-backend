from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr


class UserSchema(BaseModel):
    id: Optional[int] = None
    name: constr(max_length=30)
    surname: constr(max_length=30)
    fathername: Optional[constr(max_length=30)] = None
    org: Optional[constr(max_length=60)] = None
    inn: constr(max_length=12)
    telnum: constr(max_length=11)
    url: constr(max_length=31)
    email: constr(max_length=50)
    password: constr(min_length=8, max_length=16)
    refer_id: Optional[constr(max_length=8)] = None


class UserStatusModel(BaseModel):
    title: int


class UserStatusHistoryModel(BaseModel):
    user_id: int
    status_id: int
    description: int
    date: datetime


class UserSessionModel(BaseModel):
    user_id: int
    token: int
    useragent: int
    ip: int
    login_date: datetime
