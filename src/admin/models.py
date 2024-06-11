from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from orders.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class AdminUserModel(Base):
    __tablename__ = 'admin_user'

    id: Mapped[pk]
    name: Mapped[str]
    surname: Mapped[str]
    fathername: Mapped[str | None]
    username: Mapped[str]
    post: Mapped[str]
    password: Mapped[str]


class AdminSessionModel(Base):
    __tablename__ = 'admin_user_sessions'

    id: Mapped[pk]
    ip: Mapped[str]
    user_agent: Mapped[str]
    token: Mapped[str]
    date: Mapped[dt]
    expires: Mapped[datetime.datetime]

    user_id: Mapped[int] = mapped_column(ForeignKey('admin_user.id', ondelete='CASCADE', onupdate='CASCADE'))


class CrmSettingsModel(Base):
    __tablename__ = 'admin_crm_settings'

    id: Mapped[pk]
