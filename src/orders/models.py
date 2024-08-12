from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from products.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


# Account
class OrdersAccountModel(Base):
    __tablename__ = 'orders_account'

    id: Mapped[pk]
    number: Mapped[str]
    name: Mapped[str]
    reg_date: Mapped[datetime.date | None]
    is_active: Mapped[bool]

    # FK
    address_id: Mapped[int] = mapped_column(
        ForeignKey('orders_address.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    server_id: Mapped[int] = mapped_column(
        ForeignKey('orders_server.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    address: Mapped['OrdersAddressModel'] = relationship(lazy='noload')
    server: Mapped['PickerServerModel'] = relationship(lazy='noload')


# Contractor
class OrdersContractorModel(Base):
    __tablename__ = 'orders_contractor'

    id: Mapped[pk]
    name: Mapped[str]
    is_active: Mapped[bool]


# Address
class OrdersAddressModel(Base):
    __tablename__ = 'orders_address'

    id: Mapped[pk]
    address: Mapped[str]
    district: Mapped[str | None]
    is_active: Mapped[bool]

    # FK
    contractor_id: Mapped[int | None] = mapped_column(
        ForeignKey('orders_contractor.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    contractor: Mapped['OrdersContractorModel'] = relationship(lazy='noload')


# Order
class OrdersOrderModel(Base):
    __tablename__ = 'orders_order'

    id: Mapped[pk]

    wb_keyword: Mapped[str]
    wb_price: Mapped[int | None]
    wb_uuid: Mapped[str | None]
    wb_status: Mapped[str | None]
    wb_collect_code: Mapped[str | None]

    status: Mapped[int]
    description: Mapped[str | None]

    dt_planed: Mapped[datetime.date | None]
    dt_ordered: Mapped[datetime.date | None]
    dt_delivered: Mapped[datetime.date | None]
    dt_collected: Mapped[datetime.date | None]

    # FK
    size_id: Mapped[int] = mapped_column(
        ForeignKey('products_product_size.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey('orders_account.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    size: Mapped['ProductSizeModel'] = relationship(lazy='noload')
    account: Mapped['OrdersAccountModel'] = relationship(lazy='noload')
