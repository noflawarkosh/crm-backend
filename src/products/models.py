from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from payments.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class ProductModel(Base):
    __tablename__ = 'products_product'

    id: Mapped[pk]
    org_id: Mapped[int] = mapped_column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE'))
    barcode: Mapped[str]
    unicode: Mapped[str | None]
    date: Mapped[dt]
    is_active: Mapped[bool]

    wb_article: Mapped[str]
    wb_title: Mapped[str]
    wb_size: Mapped[str | None]
    wb_price: Mapped[str]
