import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel, UserSessionModel
from auth.router import authed

from database import DefaultRepository
from orders.models import OrdersOrderModel
from orders.schemas import OrdersOrderReadModel, OrdersOrderCreateModel
from orgs.router import check_access
from products.models import ProductModel, ProductSizeModel
from strings import *

from products.repository import ProductsRepository

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.get('/getPlan')
async def get_plan(org_id: int, date: datetime.datetime, session: UserSessionModel = Depends(authed)
                   ) -> list[OrdersOrderReadModel]:
    await check_access(org_id, session.user.id, 4)

    records = await DefaultRepository.get_records(
        model=OrdersOrderModel,
        filters=[OrdersOrderModel.org_id == org_id, OrdersOrderModel.dt_planed == date],
        prefetch_related=[OrdersOrderModel.size, OrdersOrderModel.product]
    )

    return [OrdersOrderReadModel.model_validate(record, from_attributes=True) for record in records]


@router.post('/savePlan')
async def save_data(amount: int,
                    data: Annotated[OrdersOrderCreateModel, Depends()],
                    session: UserSessionModel = Depends(authed)):
    await check_access(data.org_id, session.user.id, 4)

    if amount > 100:
        raise HTTPException(status_code=400, detail=string_orders_max_amount)

    products = await DefaultRepository.get_records(
        model=ProductModel,
        filters=[ProductModel.id == data.product_id, ProductModel.org_id == data.org_id, ProductModel.status != 3],
        select_related=[ProductModel.sizes]
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    if not data.size_id:
        raise HTTPException(status_code=400, detail=string_product_size_not_selected)

    if data.size_id not in [size.id for size in products[0].sizes]:
        raise HTTPException(status_code=400, detail=string_403)

    sizes = await DefaultRepository.get_records(ProductSizeModel, filters=[ProductSizeModel.id == data.size_id])

    if len(sizes) != 1:
        raise HTTPException(status_code=404, detail=string_product_size_not_found)

    size = sizes[0]

    if not size.is_active:
        raise HTTPException(status_code=403, detail=string_product_size_not_active)

    if not size.barcode:
        raise HTTPException(status_code=403, detail=string_product_size_no_barcode)

    if not size.wb_in_stock:
        raise HTTPException(status_code=403, detail=string_product_size_not_in_stock)

    if not size.wb_price:
        raise HTTPException(status_code=403, detail=string_product_size_no_price)

    if data.dt_planed.date() < datetime.datetime.now().date():
        raise HTTPException(status_code=403, detail=string_orders_wrong_date)

    if datetime.datetime.now().hour > 9 and data.dt_planed.date() == datetime.datetime.now().date():
        raise HTTPException(status_code=400, detail=string_orders_time_error)

    await DefaultRepository.save_records([{
        'model': OrdersOrderModel,
        'records': [{
            **data.model_dump(),
            'status': 1,
        }] * amount
    }])
