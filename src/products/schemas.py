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
    is_active: bool


class ProductSizeReadSchema(ProductSizeCreateSchema):
    id: int
    product: Optional['ProductReadSchema']


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
    last_update: datetime.datetime

    sizes: Optional[list[ProductSizeReadSchema]]


# Review schemas
class ReviewMediaReadSchema(BaseModel):
    id: int
    review_id: int
    media: str | None


class ReviewCreateSchema(BaseModel):
    text: Optional[str] = None
    size_id: Optional[int] = None
    match: Optional[int]
    strict_match: bool
    is_express: bool = False
    stars: int
    advs: Optional[str] = None
    disadvs: Optional[str] = None


class ReviewUpdateSchema(BaseModel):
    id: int
    text: Optional[str] = None
    match: Optional[int]
    strict_match: bool
    is_express: bool
    stars: int
    advs: Optional[str] = None
    disadvs: Optional[str] = None


class ReviewReadSchema(BaseModel):
    id: int
    text: str | None
    match: int | None
    status: int
    description: Optional[str] = None
    strict_match: bool
    is_express: bool
    stars: int
    advs: Optional[str] = None
    disadvs: Optional[str] = None

    media: Optional[list[ReviewMediaReadSchema]] = None
    size: Optional[ProductSizeReadSchema]
