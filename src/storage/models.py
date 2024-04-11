from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from orgs.models import Base
import datetime

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class StorageModel(Base):
    __tablename__ = 'storage'

    id: Mapped[pk]
    title: Mapped[str]
    description: Mapped[str | None]
    storage_href: Mapped[str]
    type: Mapped[str]
    date: Mapped[dt]
    owner_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
