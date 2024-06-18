from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from products.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


# Server
class OrdersServerContractorModel(Base):
    __tablename__ = 'orders_server_contractor'

    id: Mapped[pk]
    load_percent: Mapped[float]
    load_j_min: Mapped[int]
    load_j_max: Mapped[int]
    load_l_min: Mapped[int]
    load_l_max: Mapped[int]
    load_t_min: Mapped[int]
    load_t_max: Mapped[int]
    load_i: Mapped[int]
    load_m: Mapped[datetime.datetime]

    # FK
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey('orders_contractor.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    server_id: Mapped[int] = mapped_column(
        ForeignKey('orders_server.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    contractor: Mapped['OrdersContractorModel'] = relationship(lazy=False)


class OrdersServerScheduleModel(Base):
    __tablename__ = 'orders_server_schedule'

    id: Mapped[pk]
    title: Mapped[str]
    time_min_min_per_step: Mapped[float]
    time_max_min_per_step: Mapped[float]
    time_start: Mapped[datetime.time]
    time_end: Mapped[datetime.time]
    time_first_point: Mapped[datetime.time]
    time_second_point: Mapped[datetime.time]


class OrdersServerModel(Base):
    __tablename__ = 'orders_server'

    id: Mapped[pk]
    number: Mapped[str]
    name: Mapped[str]
    is_active: Mapped[bool]

    # FK
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey('orders_server_schedule.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    schedule: Mapped['OrdersServerScheduleModel'] = relationship(lazy=False)
    contractors: Mapped[list['OrdersServerContractorModel']] = relationship(lazy=False)


# Account
class OrdersAccountModel(Base):
    __tablename__ = 'orders_account'

    id: Mapped[pk]
    number: Mapped[str]
    name: Mapped[str]
    reg_date: Mapped[dt]
    is_active: Mapped[bool]

    # FK
    address_id: Mapped[int] = mapped_column(
        ForeignKey('orders_address.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    server_id: Mapped[int] = mapped_column(
        ForeignKey('orders_server.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    address: Mapped['OrdersAddressModel'] = relationship(lazy=False)
    server: Mapped['OrdersServerModel'] = relationship(lazy=False)


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
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey('orders_contractor.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    contractor: Mapped['OrdersContractorModel'] = relationship(lazy=False)


# Order
class OrdersOrderModel(Base):
    __tablename__ = 'orders_order'

    id: Mapped[pk]
    wb_uuid: Mapped[str | None]
    wb_keyword: Mapped[str]
    wb_price: Mapped[int | None]
    description: Mapped[str | None]
    dt_planed: Mapped[datetime.datetime | None]
    dt_ordered: Mapped[datetime.datetime | None]
    dt_delivered: Mapped[datetime.datetime | None]
    dt_collected: Mapped[datetime.datetime | None]

    # FK
    product_id: Mapped[int] = mapped_column(
        ForeignKey('products_product.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    size_id: Mapped[int] = mapped_column(
        ForeignKey('products_product_size.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey('orders_account.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    product: Mapped['ProductModel'] = relationship()
    size: Mapped['ProductSizeModel'] = relationship()
    account: Mapped['OrdersAccountModel'] = relationship()
    organization: Mapped['OrganizationModel'] = relationship()
