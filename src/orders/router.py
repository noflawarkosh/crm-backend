import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserSessionModel
from auth.router import authed

from database import Repository
from orders.models import OrdersOrderModel
from orders.schemas import OrdersOrderReadModel, OrdersOrderCreateModel
from orgs.router import check_access
from products.models import ProductModel, ProductSizeModel
from strings import *

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.post('/cancelTask')
async def cancel_task(task_id: int, session: UserSessionModel = Depends(authed)):
    records = await Repository.get_records(
        model=OrdersOrderModel,
        select_related=[OrdersOrderModel.size],
        deep_related=[[OrdersOrderModel.size, ProductSizeModel.product]],
        joins=[ProductSizeModel, ProductModel],
        filtration=[OrdersOrderModel.id == task_id]
    )

    if len(records) != 1:
        raise HTTPException(status_code=404, detail=string_orders_task_not_found)

    record = records[0]

    await check_access(record.size.product.org_id, session.user.id, 4)

    if record.status != 1:
        raise HTTPException(status_code=400, detail=string_403)

    await Repository.save_records([{
        'model': OrdersOrderModel,
        'records': [
            {
                'id': task_id,
                'status': 7,
            }]
    }])


@router.get('/getPlan')
async def get_plan(org_id: int, date: datetime.datetime, session: UserSessionModel = Depends(authed)
                   ) -> list[OrdersOrderReadModel]:
    await check_access(org_id, session.user.id, 4)

    records = await Repository.get_records(
        model=OrdersOrderModel,
        filters=[OrdersOrderModel.dt_planed == date],
        select_related=[OrdersOrderModel.size],
        deep_related=[[OrdersOrderModel.size, ProductSizeModel.product]],
        joins=[ProductSizeModel, ProductModel],
        filtration=[ProductModel.org_id == org_id]
    )

    return [OrdersOrderReadModel.model_validate(record, from_attributes=True) for record in records]

@router.get('/getOrders')
async def get_plan(org_id: int, session: UserSessionModel = Depends(authed)
                   ) -> list[OrdersOrderReadModel]:
    await check_access(org_id, session.user.id, 4)

    records = await Repository.get_records(
        model=OrdersOrderModel,
        filters=[OrdersOrderModel.status != 1],
        select_related=[OrdersOrderModel.size],
        deep_related=[[OrdersOrderModel.size, ProductSizeModel.product]],
        joins=[ProductSizeModel, ProductModel],
        filtration=[ProductModel.org_id == org_id]
    )

    return [OrdersOrderReadModel.model_validate(record, from_attributes=True) for record in records]

@router.post('/savePlan')
async def save_data(amount: int, data: Annotated[OrdersOrderCreateModel, Depends()],
                    session: UserSessionModel = Depends(authed)):
    if amount > 100:
        raise HTTPException(status_code=400, detail=string_orders_max_amount)

    sizes = await Repository.get_records(
        ProductSizeModel,
        filters=[ProductSizeModel.id == data.size_id],
        select_related=[ProductSizeModel.product]
    )

    if len(sizes) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    size = sizes[0]

    records = await Repository.get_records(
        model=OrdersOrderModel,
        filters=[OrdersOrderModel.dt_planed == data.dt_planed],
        select_related=[OrdersOrderModel.size],
        deep_related=[[OrdersOrderModel.size, ProductSizeModel.product]],
        joins=[ProductSizeModel, ProductModel],
        filtration=[ProductModel.org_id == size.product.org_id]
    )

    if len(records) + amount > 500:
        raise HTTPException(status_code=403, detail=string_products_max_tasks_per_day)

    if size.product.status == 3:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    await check_access(size.product.org_id, session.user.id, 8)

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

    await Repository.save_records([{
        'model': OrdersOrderModel,
        'records': [{
            **data.model_dump(),
            'status': 1,
        }] * amount
    }])
