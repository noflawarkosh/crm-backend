import datetime
from typing import Optional
from pydantic import BaseModel, constr
from storage.schemas import StorageGETSchema


# Product Size schemas
class ProductSizeCreateSchema(BaseModel):
    wb_size_name: str | None
    wb_size_origName: str | None
    wb_size_optionId: int
    wb_in_stock: bool
    wb_price: int | None


class ProductSizeReadSchema(ProductSizeCreateSchema):
    id: int


# Product schemas
class ProductPOSTSchema(BaseModel):
    org_id: int
    barcode: str
    wb_url: str


class ProductCreateSchema(BaseModel):
    org_id: int
    barcode: str
    wb_article: str
    wb_title: str


class ProductReadSchema(BaseModel):
    id: int
    barcode: str
    date: datetime.datetime
    is_active: bool
    wb_article: str
    wb_title: str
    org_id: int
    media_id: int | None

    media: Optional[StorageGETSchema]
    sizes: Optional[list[ProductSizeReadSchema]]


# Review schemas
class ReviewMediaReadSchema(BaseModel):
    id: int
    review_id: int
    media_id: int

    media: StorageGETSchema


class ReviewCreateSchema(BaseModel):
    text: Optional[str] = None
    product_id: int
    size_id: Optional[int] = None
    match: Optional[int] = None


class ReviewReadSchema(ReviewCreateSchema):
    id: int
    text: str | None
    match: int | None
    status: int

    media: Optional[list[ReviewMediaReadSchema]]
    product: Optional[ProductReadSchema]
    size: Optional[ProductSizeReadSchema]



