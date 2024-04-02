from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr


class UserSchema(BaseModel):
    id: Optional[int] = None
    name: constr(max_length=100)
    username: constr(min_length=5, max_length=20)
    email: constr(max_length=100)
    telnum: constr(max_length=11)
    telegram: constr(max_length=50)
    password: constr(min_length=8, max_length=16)

class LoginSchema(BaseModel):
    username: constr(min_length=5, max_length=20)
    password: constr(min_length=8, max_length=16)

