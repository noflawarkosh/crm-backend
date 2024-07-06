import random
import string
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, Response, Request, HTTPException, UploadFile, File
from datetime import datetime, timedelta

from sqlalchemy import func, inspect

from admin.models import AdminSessionModel, AdminUserModel, PickerSettingsModel, CrmSettingsModel, PickerHistoryModel

from admin.schemas import AdminSessionCreateSchema
from admin.utils import set_type, verify_file, generate_filename, s3_save, refresh_active_and_collected, \
    generate_plan_xlsx, identify_orders_xlsx
from auth.models import UserModel, UserSessionModel

from auth.utils import hash_password, generate_token
from database import DefaultRepository
from orders.models import OrdersAddressModel, OrdersOrderModel, OrdersContractorModel, OrdersServerScheduleModel, \
    OrdersServerModel, OrdersServerContractorModel, OrdersAccountModel
from orgs.models import OrganizationModel
from payments.models import BalanceBillModel, BalanceSourceModel, BalancePricesModel, BalanceHistoryModel
from products.models import ProductModel, ReviewModel, ProductSizeModel
from products.repository import ProductsRepository
from products.utils import parse_wildberries_card
from strings import *

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

tables_access = {
    'users': (UserModel, 4096, {}),
    'organizations': (OrganizationModel, 2048, {}),
    'organizations_full': (OrganizationModel, 2048, {'select_related': [OrganizationModel.owner]}),
    'sizes': (ProductSizeModel, 64, {}),
    'orgs': (OrganizationModel, 2048, {}),
    'bills': (BalanceBillModel, 256, {}),
    'balance': (BalanceHistoryModel, 256, {}),
    'orders': (OrdersOrderModel, 16, {}),
    'addresses': (OrdersAddressModel, 256, {}),
    'accounts': (OrdersAccountModel, 32, {'select_related': [OrdersAccountModel.address, OrdersAccountModel.server]}),
    'addresses_full': (OrdersAddressModel, 256, {'select_related': [OrdersAddressModel.contractor]}),
    'products': (ProductModel, 64, {}),
    'reviews': (ReviewModel, 128, {}),
    'admins': (AdminUserModel, 16384, {}),
    'usersessions': (UserSessionModel, 65536, {}),
    'adminsessions': (AdminSessionModel, 131072, {}),
    'contractors': (OrdersContractorModel, 8, {}),
    'banks': (BalanceSourceModel, 1024, {}),
    'prices': (BalancePricesModel, 512, {}),
    'schedules': (OrdersServerScheduleModel, 524288, {}),
    'servercontractors': (OrdersServerContractorModel, 8, {}),
    'pickersettings': (PickerSettingsModel, 2, {}),
    'settings': (CrmSettingsModel, 262144, {}),
    'pickerhistory': (PickerHistoryModel, 2, {}),

    'servers': (
        OrdersServerModel, 1,
        {
            'prefetch_related': [
                OrdersServerModel.schedule,
                OrdersServerModel.contractors,
            ],
        }
    ),
    'bills_full': (
        BalanceBillModel, 256,
        {
            'select_related': [
                BalanceBillModel.organization,
                BalanceBillModel.source,
                BalanceBillModel.status,
            ]
        }
    ),
}


async def every(request: Request = Request):
    token = request.cookies.get(cookies_admin_token_key)

    if not token:
        return None

    sessions = await DefaultRepository.get_records(
        AdminSessionModel,
        filters=[AdminSessionModel.token == token, AdminSessionModel.expires > func.now()],
        select_related=[AdminSessionModel.admin]
    )

    if len(sessions) != 1:
        return None

    session = sessions[0]

    if not session or session.ip != request.client.host or session.user_agent != request.headers.get('user-agent'):
        return None

    return session


async def authed(request: Request = Request):
    result = await every(request)
    if not result:
        raise HTTPException(status_code=401, detail=string_401)
    return result


async def not_authed(request: Request = Request):
    result = await every(request)
    if result:
        raise HTTPException(status_code=409, detail=string_409)
    return result


@router.post('/login')
async def login(request: Request, response: Response, username: str, password: str,
                session: AdminSessionModel = Depends(not_authed)):
    admin_check = await DefaultRepository.get_records(
        AdminUserModel,
        filters=[AdminUserModel.username == username.lower().replace(' ', '')]
    )

    if len(admin_check) != 1:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if hash_password(password) != admin_check[0].password:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    token = generate_token(256)
    await DefaultRepository.save_records([
        {
            'model': AdminSessionModel,
            'records': [
                {
                    'user_id': admin_check[0].id,
                    'token': token,
                    'user_agent': request.headers.get('user-agent'),
                    'ip': request.client.host,
                    'expires': datetime.now() + timedelta(days=3)
                }
            ]
        }
    ])

    response.set_cookie(key=cookies_admin_token_key, value=token)


@router.get('/logout')
async def logout(response: Response, session: AdminSessionModel = Depends(authed)):
    await DefaultRepository.save_records([
        {'model': AdminSessionModel, 'records': [{'id': session.id, 'expires': func.now()}]}
    ])
    response.delete_cookie(cookies_admin_token_key)


@router.get('/profile')
async def logout(response: Response, session: AdminSessionModel = Depends(authed)):
    data = session.admin.__dict__
    del data['password']
    return data


@router.get('/get/{section}')
async def reading_data(request: Request, section: str, session: AdminSessionModel = Depends(authed)):
    if not tables_access.get(section, None):
        raise HTTPException(status_code=404, detail=string_404)

    model, level, default_kwargs = tables_access[section]

    if not level & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    kwargs = default_kwargs.copy()
    params = request.query_params.multi_items()

    if params:
        filters = []
        for key, value in params:
            field = getattr(model, key)
            filters.append(field == set_type(value, str(field.type)))

        if kwargs.get('filters', None):
            kwargs['filters'] = kwargs['filters'] + filters

        else:
            kwargs['filters'] = filters

    records = await DefaultRepository.get_records(model, **kwargs)

    return [record.__dict__ for record in records]


@router.get('/fields/{section}')
async def reading_fields(section: str, session: AdminSessionModel = Depends(authed)):
    if not tables_access.get(section, None):
        raise HTTPException(status_code=404, detail=string_404)

    model, level, select_models = tables_access[section]

    if not level & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    mapper = inspect(model)
    fields = {}

    for column in mapper.columns:
        fields[column.name] = str(column.type)

    return fields


@router.post('/save')
async def creating_data(data: dict[str, list[dict]], request: Request, session: AdminSessionModel = Depends(authed)):
    models_with_typed_records = []

    for section in data:

        if not tables_access.get(section, None):
            raise HTTPException(status_code=404, detail=string_404)

        model, level, select_models = tables_access[section]

        if not level & session.admin.level:
            raise HTTPException(status_code=403, detail=string_403)

        mapper = inspect(model)
        model_fields = {}

        for column in mapper.columns:
            model_fields[column.name] = str(column.type)

        model_with_typed_records = []

        for record in data[section]:
            model_record_with_typed_values = {}
            for field, value in record.items():

                typed_value = set_type(value, model_fields[field])

                if field == 'password':
                    typed_value = hash_password(str(typed_value))

                model_record_with_typed_values[field] = typed_value

            model_with_typed_records.append(model_record_with_typed_values)

        models_with_typed_records.append({
            'model': model,
            'records': model_with_typed_records
        })

    await DefaultRepository.save_records(models_with_typed_records)


@router.delete('/delete/{section}/{record_id}')
async def reading_fields(section: str, record_id: int, session: AdminSessionModel = Depends(authed)):
    if not tables_access.get(section, None):
        raise HTTPException(status_code=404, detail=string_404)

    model, level, select_models = tables_access[section]

    if not level & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    await DefaultRepository.delete_record(model, record_id)


@router.post('/uploadBillMedia')
async def test(bill_id: int, file: UploadFile = File(), session: AdminSessionModel = Depends(authed)):
    try:
        await verify_file(file, ['image', 'other'])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")

    bills = await DefaultRepository.get_records(BalanceBillModel, filters=[BalanceBillModel.id == bill_id])

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404)
    bill = bills[0]

    content = await file.read()
    n, t = await s3_save(content, generate_filename(), file.filename.rsplit('.', maxsplit=1)[1])

    record = {'id': bill.id, 'media': f'{n}.{t}'}

    if bill.status_id == 6:
        record['status_id'] = 3

    await DefaultRepository.save_records([
        {'model': BalanceBillModel, 'records': [record]}
    ])


@router.post('/refreshOrders')
async def refresh_orders(request: Request, session: AdminSessionModel = Depends(authed)):
    data = dict(await request.form())

    servers = await DefaultRepository.get_records(
        OrdersServerModel,
        filters=[OrdersServerModel.is_active],
        select_related=[OrdersServerModel.contractors, OrdersServerModel.schedule]
    )

    for server in servers:
        if not data.get(f'active-{server.id}', None) or data.get(f'active-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с активными заказами для {server.name}')

        if not data.get(f'collected-{server.id}', None) or data.get(f'collected-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с полученными заказами для {server.name}')

    try:
        return await refresh_active_and_collected(data, servers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'{str(e)}')


@router.post('/generatePlan')
async def generate_plan(request: Request, session: AdminSessionModel = Depends(authed)):
    servers = await DefaultRepository.get_records(
        OrdersServerModel,
        filters=[OrdersServerModel.is_active],
        select_related=[OrdersServerModel.contractors, OrdersServerModel.schedule]
    )

    data = dict(await request.form())
    bad_accounts = data['bad_accounts']

    try:
        await generate_plan_xlsx(servers, bad_accounts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'{str(e)}')


@router.post('/identifyOrders')
async def identify_orders(request: Request, session: AdminSessionModel = Depends(authed)):
    data = dict(await request.form())
    if not data.get('orders') or data.get('orders') == 'undefined':
        raise HTTPException(status_code=400, detail='Выберите файл с заказами')

    try:
        return await identify_orders_xlsx(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'{str(e)}')



