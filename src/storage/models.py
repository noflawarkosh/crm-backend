from typing import Annotated
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
import datetime

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]

class UserModel(Base):
    __tablename__ = 'storage'

    id: Mapped[pk]
    title: Mapped[str]
    description: Mapped[str]
    storage_href: Mapped[str]
    type: Mapped[int]




