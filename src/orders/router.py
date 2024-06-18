import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel
from auth.router import authed
from auth.schemas import UserSessionReadSchema
from orders.schemas import OrdersOrderReadModel, OrdersOrderCreateModel
from orgs.utils import check_access
from strings import *

from orders.repository import OrdersRepository
from products.repository import ProductsRepository

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.get('/getPlan')
async def get_data(org_id: int,
                   date: datetime.datetime,
                   session: UserSessionReadSchema = Depends(authed)):
    try:
        await check_access(org_id, session.user.id, 4)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    records = await OrdersRepository.read_plan(org_id, date)

    return [OrdersOrderReadModel.model_validate(record, from_attributes=True) for record in records]


@router.post('/savePlan')
async def save_data(amount: int,
                    data: Annotated[OrdersOrderCreateModel, Depends()],
                    session: UserSessionReadSchema = Depends(authed)):
    try:
        await check_access(data.org_id, session.user.id, 4)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    if amount > 500:
        raise HTTPException(status_code=400, detail=string_orders_max_amount)

    product = await ProductsRepository.get_one_by_id(data.product_id)

    if (
            not product or
            product.org_id != data.org_id or
            not product.is_active or
            data.size_id not in [size.id for size in product.sizes] or
            data.dt_planed.date() < datetime.datetime.now().date()
    ):
        raise HTTPException(status_code=403, detail=string_403)

    if datetime.datetime.now().hour > 9 and data.dt_planed.date() == datetime.datetime.now().date():
        raise HTTPException(status_code=400, detail=string_orders_time_error)

    await OrdersRepository.save_plan(data.model_dump(), amount)
