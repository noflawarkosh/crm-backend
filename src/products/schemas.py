import datetime
from typing import Optional
from pydantic import BaseModel, constr


class ProductPOSTSchema(BaseModel):
    org_id: int
    barcode: str
    wb_article: str


class ProductGETSchema(ProductPOSTSchema):
    id: int
    unicode: str | None
    date: datetime.datetime
    is_active: bool
    wb_title: str
    wb_size: str
    wb_price: str
