import datetime
from typing import Optional
from pydantic import BaseModel, constr
from storage.schemas import StorageGETSchema


# Product Size schemas
class ProductSizeInsertSchema(BaseModel):
    wb_size_name: str | None
    wb_size_origName: str | None
    wb_size_optionId: int
    wb_in_stock: bool
    wb_price: int | None


class ProductSizeGETSchema(ProductSizeInsertSchema):
    id: int


# Product schemas
class ProductPOSTSchema(BaseModel):
    org_id: int
    barcode: str
    wb_url: str


class ProductInsertSchema(BaseModel):
    org_id: int
    barcode: str
    wb_article: str
    wb_title: str


class ProductNonRelGETSchema(BaseModel):
    id: int
    barcode: str
    date: datetime.datetime
    is_active: bool
    wb_article: str
    wb_title: str

    org_id: int
    media_id: int | None


class ProductGETSchema(BaseModel):
    id: int
    barcode: str
    date: datetime.datetime
    is_active: bool
    wb_article: str
    wb_title: str

    org_id: int

    media: StorageGETSchema | None
    sizes: list[ProductSizeGETSchema]


# Review schemas
class ReviewMediaGETSchema(BaseModel):
    id: int

    review_id: int
    media_id: int

    media: StorageGETSchema


class ReviewStatusGETSchema(BaseModel):
    id: int
    title: str


class ReviewMatchGETSchema(BaseModel):
    id: int
    title: str


class ReviewStatusHistoryGETSchema(BaseModel):
    id: int
    review_id: int
    status_id: int
    description: str | None
    date: datetime.datetime
    status: ReviewStatusGETSchema


class ReviewPOSTSchema(BaseModel):
    text: Optional[str] = None

    product_id: int
    size_id: Optional[int] = None
    match_id: Optional[int] = None


class ReviewGETSchema(ReviewPOSTSchema):
    id: int
    text: str | None

    media: list[ReviewMediaGETSchema] | None
    statuses: list[ReviewStatusHistoryGETSchema]
    product: ProductGETSchema
    size: ProductSizeGETSchema | None
    match: ReviewMatchGETSchema | None
