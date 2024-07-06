import datetime
from typing import Optional
from pydantic import BaseModel, constr
from products.schemas import ProductReadSchema, ProductSizeReadSchema


class OrdersOrderCreateModel(BaseModel):
    wb_keyword: str
    dt_planed: datetime.datetime
    size_id: int


class OrdersOrderReadModel(OrdersOrderCreateModel):
    id: int
    description: Optional[str]
    status: int
    dt_ordered: Optional[datetime.datetime]
    dt_delivered: Optional[datetime.datetime]
    dt_collected: Optional[datetime.datetime]

    size: 'ProductSizeReadSchema'
