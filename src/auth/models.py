from typing import Annotated
from sqlalchemy import MetaData, Integer, String, TIMESTAMP, ForeignKey, Table, Column, text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
import datetime

metadata = MetaData()

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class UserModel(Base):
    __tablename__ = 'user'

    id: Mapped[pk]
    name: Mapped[str]
    username: Mapped[str]
    email: Mapped[str]
    telnum: Mapped[str]
    telegram: Mapped[str]
    password: Mapped[str]


class UserStatusModel(Base):
    __tablename__ = 'user_status'

    id: Mapped[pk]
    title: Mapped[str]


class UserStatusHistoryModel(Base):
    __tablename__ = 'user_status_history'

    id: Mapped[pk]
    user_id: Mapped[int]
    status_id: Mapped[int]
    description: Mapped[str | None]
    date: Mapped[dt]


class UserSessionModel(Base):
    __tablename__ = 'user_session'

    id: Mapped[pk]
    user_id: Mapped[int]
    token: Mapped[str]
    useragent: Mapped[str]
    ip: Mapped[str]
    login_date: Mapped[dt]
