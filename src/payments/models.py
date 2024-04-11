from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from database import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class BalanceActionModel(Base):
    __tablename__ = 'balance_action'
    id: Mapped[pk]
    title: Mapped[str]


class BalanceHistoryModel(Base):
    __tablename__ = 'balance_history'

    id: Mapped[pk]
    action_id: Mapped[int]
    org_id: Mapped[int]
    amount: Mapped[float]


class BalanceRequest(Base):
    __tablename__ = 'balance_request'

    id: Mapped[pk]
    org_id: Mapped[int]
    amount: Mapped[float]
    source_id: Mapped[int]


class BalanceRequestMedia(Base):
    __tablename__ = 'balance_request_media'

    id: Mapped[pk]
    request_id: Mapped[int]
    media_id: Mapped[int]


class BalanceSource(Base):
    __tablename__ = 'balance_source'
    id: Mapped[pk]
    title: Mapped[str]
    description: Mapped[str]
    number: Mapped[str]
    is_active: Mapped[bool]
