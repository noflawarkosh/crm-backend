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
    level: Mapped[int]
    password: Mapped[str]


class AdminSessionModel(Base):
    __tablename__ = 'admin_user_sessions'

    id: Mapped[pk]
    ip: Mapped[str]
    user_agent: Mapped[str]
    token: Mapped[str]
    date: Mapped[dt]
    expires: Mapped[datetime.datetime]

    user_id: Mapped[int] = mapped_column(
        ForeignKey('admin_user.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    admin: Mapped[AdminUserModel] = relationship(lazy=False)


class CrmSettingsModel(Base):
    __tablename__ = 'admin_crm_settings'

    id: Mapped[pk]
    crm_maintenance: Mapped[bool]


class PickerSettingsModel(Base):
    __tablename__ = 'admin_picker_settings'

    id: Mapped[pk]
    r2: Mapped[float]
    r3: Mapped[float]
    r4: Mapped[float]

    l2: Mapped[float]
    l3: Mapped[float]
    l4: Mapped[float]
    l5: Mapped[float]

    lo: Mapped[int]
    al: Mapped[int]

    k_format: Mapped[str]


class PickerHistoryModel(Base):
    __tablename__ = 'admin_picker_history'

    id: Mapped[pk]
    date: Mapped[dt]
    logs: Mapped[str]
    result: Mapped[str | None]

    # FK
    server_id: Mapped[int] = mapped_column(
        ForeignKey('orders_server.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    server: Mapped['OrdersServerModel'] = relationship(lazy=False)
