import datetime
from typing import Optional
from pydantic import BaseModel, constr
from products.schemas import ProductReadSchema, ProductSizeReadSchema


class OrdersOrderCreateModel(BaseModel):
    wb_keyword: str
    dt_planed: datetime.datetime
    product_id: int
    size_id: int
    org_id: int


class OrdersOrderReadModel(OrdersOrderCreateModel):
    id: int
    wb_price: Optional[int]
    description: Optional[str]
    status: int
    dt_ordered: Optional[datetime.datetime]
    dt_delivered: Optional[datetime.datetime]
    dt_collected: Optional[datetime.datetime]

    product: 'ProductReadSchema'
    size: 'ProductSizeReadSchema'
4