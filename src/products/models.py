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
    barcode: Mapped[str]
    date: Mapped[dt]
    is_active: Mapped[bool] = mapped_column(default=True)
    wb_article: Mapped[str]
    wb_title: Mapped[str]

    # FK
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey('storage.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    media: Mapped['StorageModel'] = relationship(lazy=False)
    sizes: Mapped[list['ProductSizeModel']] = relationship(lazy=False)


class ProductSizeModel(Base):
    __tablename__ = 'products_product_size'

    id: Mapped[pk]
    wb_size_name: Mapped[str | None]
    wb_size_origName: Mapped[str | None]
    wb_size_optionId: Mapped[int]
    wb_in_stock: Mapped[bool]
    wb_price: Mapped[int | None]

    # FK
    product_id: Mapped[int] = mapped_column(
        ForeignKey('products_product.id', ondelete='CASCADE', onupdate='CASCADE')
    )


class ReviewModel(Base):
    __tablename__ = 'products_review'

    id: Mapped[pk]
    text: Mapped[str | None]

    # FK
    product_id: Mapped[int] = mapped_column(
        ForeignKey('products_product.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    size_id: Mapped[int | None] = mapped_column(
        ForeignKey('products_product_size.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    match_id: Mapped[int | None] = mapped_column(
        ForeignKey('products_review_match.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    media: Mapped[list['ReviewMediaModel']] = relationship(lazy=False)
    statuses: Mapped[list['ReviewStatusHistoryModel']] = relationship(lazy=False)
    product: Mapped['ProductModel'] = relationship(lazy=False)
    size: Mapped['ProductSizeModel'] = relationship(lazy=False)
    match: Mapped['ReviewMatchModel'] = relationship(lazy=False)


class ReviewMatchModel(Base):
    __tablename__ = 'products_review_match'

    id: Mapped[pk]
    title: Mapped[str]


class ReviewMediaModel(Base):
    __tablename__ = 'products_review_media'

    id: Mapped[pk]

    # FK
    review_id: Mapped[int] = mapped_column(
        ForeignKey('products_review.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey('storage.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    media: Mapped['StorageModel'] = relationship(lazy=False)


class ReviewStatusModel(Base):
    __tablename__ = 'products_review_status'

    id: Mapped[pk]
    title: Mapped[str]


class ReviewStatusHistoryModel(Base):
    __tablename__ = 'products_review_status_history'

    id: Mapped[pk]
    description: Mapped[str | None]
    date: Mapped[dt]

    # FK
    review_id: Mapped[int] = mapped_column(
        ForeignKey('products_review.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey('products_review_status.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationship
    status: Mapped[ReviewStatusModel] = relationship(lazy=False)
