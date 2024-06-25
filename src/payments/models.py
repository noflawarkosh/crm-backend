from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from orgs.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


# Prices
class BalancePricesModel(Base):
    __tablename__ = 'balance_prices'

    id: Mapped[pk]
    title: Mapped[str]
    number: Mapped[int]
    amount: Mapped[int]

    price_buy: Mapped[int]
    price_collect: Mapped[int]
    price_review: Mapped[int]
    price_review_media: Mapped[int]
    price_review_request: Mapped[int]
    price_box: Mapped[int]
    price_pass: Mapped[int]
    price_percent: Mapped[int]
    price_percent_limit: Mapped[int]
    price_percent_penalty: Mapped[int]


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
    organization: Mapped['OrganizationModel'] = relationship(lazy='noload')
    action: Mapped['BalanceActionModel'] = relationship(lazy='noload')


class BalanceBillStatusModel(Base):
    __tablename__ = 'balance_bill_status'

    id: Mapped[pk]
    title: Mapped[str]


class BalanceBillModel(Base):
    __tablename__ = 'balance_bill'

    id: Mapped[pk]
    date: Mapped[dt]
    amount: Mapped[int]
    media: Mapped[str | None]

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

    # Relationships
    organization: Mapped['OrganizationModel'] = relationship(lazy='noload')
    source: Mapped['BalanceSourceModel'] = relationship(lazy='noload')
    status: Mapped['BalanceBillStatusModel'] = relationship(lazy='noload')


class BalanceSourceModel(Base):
    __tablename__ = 'balance_source'

    id: Mapped[pk]
    bank: Mapped[str]
    recipient: Mapped[str]
    number: Mapped[str]
    bill: Mapped[str]
    description: Mapped[str | None]
    is_active: Mapped[bool]
