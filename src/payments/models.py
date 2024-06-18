from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from storage.models import Base, StorageModel

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class BalanceActionModel(Base):
    __tablename__ = 'balance_action'

    id: Mapped[pk]
    title: Mapped[str]


class BalanceHistoryModel(Base):
    __tablename__ = 'balance_history'

    id: Mapped[pk]
    description: Mapped[str | None]
    amount: Mapped[int]
    date: Mapped[dt]

    # FK
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    action_id: Mapped[int] = mapped_column(
        ForeignKey('balance_action.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    organization: Mapped['OrganizationModel'] = relationship(lazy=False)
    action: Mapped['BalanceActionModel'] = relationship(lazy=False)


class BalanceBillStatusModel(Base):
    __tablename__ = 'balance_bill_status'

    id: Mapped[pk]
    title: Mapped[str]


class BalanceBillModel(Base):
    __tablename__ = 'balance_bill'

    id: Mapped[pk]
    date: Mapped[dt]
    amount: Mapped[int]

    # FK
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey('balance_source.id', onupdate='CASCADE')
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey('balance_bill_status.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey('storage.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    organization: Mapped['OrganizationModel'] = relationship(lazy=False)
    source: Mapped['BalanceSourceModel'] = relationship(lazy=False)
    status: Mapped['BalanceBillStatusModel'] = relationship(lazy=False)
    media: Mapped['StorageModel'] = relationship(lazy=False)


class BalanceSourceModel(Base):
    __tablename__ = 'balance_source'

    id: Mapped[pk]
    title: Mapped[str]
    description: Mapped[str | None]
    number: Mapped[str]
    is_active: Mapped[bool]
