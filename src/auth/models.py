import datetime
from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


# User
class UserModel(Base):
    __tablename__ = 'user'

    id: Mapped[pk]
    name: Mapped[str]
    username: Mapped[str]
    email: Mapped[str]
    telnum: Mapped[str]
    telegram: Mapped[str]
    password: Mapped[str]

    # FK
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey('storage.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    media: Mapped['StorageModel'] = relationship(primaryjoin='UserModel.media_id == StorageModel.id', lazy=False)
    statuses: Mapped[list['UserStatusHistoryModel']] = relationship(lazy=False)


# Status
class UserStatusModel(Base):
    __tablename__ = 'user_status'

    id: Mapped[pk]
    title: Mapped[str]


class UserStatusHistoryModel(Base):
    __tablename__ = 'user_status_history'

    id: Mapped[pk]
    description: Mapped[str | None]
    date: Mapped[dt]

    # FK
    user_id: Mapped[int] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey('user_status.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    status: Mapped['UserStatusModel'] = relationship(lazy=False)


# Session
class UserSessionModel(Base):
    __tablename__ = 'user_session'

    id: Mapped[pk]
    token: Mapped[str]
    useragent: Mapped[str]
    ip: Mapped[str]
    login_date: Mapped[dt]
    is_active: Mapped[bool] = mapped_column(default=True)

    # FK
    user_id: Mapped[int] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    user: Mapped['UserModel'] = relationship(lazy=False)
