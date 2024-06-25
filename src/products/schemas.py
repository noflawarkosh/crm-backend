import datetime
from typing import Optional
from pydantic import BaseModel, constr


# Product Size schemas
class ProductSizeCreateSchema(BaseModel):
    wb_size_name: str | None
    wb_size_origName: str | None
    wb_size_optionId: int
    wb_in_stock: bool
    wb_price: int | None
    barcode: str | None


class ProductSizeReadSchema(ProductSizeCreateSchema):
    id: int


# Product schemas
class ProductPOSTSchema(BaseModel):
    org_id: int
    wb_url: str


class ProductCreateSchema(BaseModel):
    org_id: int
    wb_article: str
    wb_title: str


class ProductReadSchema(BaseModel):
    id: int
    date: datetime.datetime
    status: int
    wb_article: str
    wb_title: str
    org_id: int
    media: Optional[str] = None

    sizes: Optional[list[ProductSizeReadSchema]]


# Review schemas
class ReviewMediaReadSchema(BaseModel):
    id: int
    review_id: int
    media: str | None


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

    media: Optional[list[ReviewMediaReadSchema]] = None
    product: Optional[ProductReadSchema]
    size: Optional[ProductSizeReadSchema]



