from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr


class AdminReadSchema(BaseModel):
    id: int
    name: str
    username: str
    fathername: str
    post: str


class AdminReadWPSchema(AdminReadSchema):
    password: str


class AdminSessionCreateSchema(BaseModel):
    token: str
    user_agent: str
    ip: str
    expires: datetime
    user_id: int


class AdminSessionReadSchema(AdminSessionCreateSchema):
    id: int
    date: datetime
