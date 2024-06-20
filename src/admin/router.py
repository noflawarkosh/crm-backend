from fastapi import APIRouter, Depends, Response, Request, HTTPException, UploadFile, File
from datetime import datetime, timedelta

from sqlalchemy import func, inspect

from admin.models import AdminSessionModel, AdminUserModel
from admin.repository import AdminRepository
from admin.schemas import AdminSessionCreateSchema
from admin.utils import set_type
from auth.models import UserModel, UserSessionModel

from auth.utils import hash_password, generate_token
from database import DefaultRepository
from orders.models import OrdersAddressModel, OrdersOrderModel, OrdersContractorModel, OrdersServerScheduleModel, \
    OrdersServerModel, OrdersServerContractorModel
from orgs.models import OrganizationModel
from payments.models import BalanceBillModel, BalanceSourceModel, BalancePricesModel
from products.models import ProductModel, ReviewModel
from storage.models import StorageModel
from strings import *

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

tables_access = {
    'users': (UserModel, 4096, {}),
    'orgs': (OrganizationModel, 2048, {}),
    'bills': (BalanceBillModel, 256, {}),
    'orders': (OrdersOrderModel, 16, {}),
    'addresses': (OrdersAddressModel, 256, {}),
    'products': (ProductModel, 64, {}),
    'reviews': (ReviewModel, 128, {}),
    'admins': (AdminUserModel, 16384, {}),
    'usersessions': (UserSessionModel, 65536, {}),
    'adminsessions': (AdminSessionModel, 131072, {}),
    'contractors': (OrdersContractorModel, 8, {}),
    'banks': (BalanceSourceModel, 1024, {}),
    'prices': (BalancePricesModel, 512, {}),
    'storage': (StorageModel, 524288, {}),
    'schedules': (OrdersServerScheduleModel, 524288, {}),
    'servercontractors': (OrdersServerContractorModel, 8, {}),
    'servers': (
        OrdersServerModel, 1,
        {
            'prefetch_related': [
                OrdersServerModel.schedule,
                OrdersServerModel.contractors,
            ],
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
                print(model_fields)
                model_record_with_typed_values[field] = set_type(value, model_fields[field])

            model_with_typed_records.append(model_record_with_typed_values)

        models_with_typed_records.append({
            'model': model,
            'records': model_with_typed_records
        })

    print(models_with_typed_records)

    await DefaultRepository.save_records(models_with_typed_records)


@router.delete('/delete/{model}/{record_id}')
async def reading_fields(model: str, record_id: int, session: AdminSessionModel = Depends(authed)):
    await AdminRepository.delete_record(model + 'Model', record_id)


@router.post('/test')
async def test(request: Request, session: AdminSessionModel = Depends(authed)):
    data = dict(await request.form())

    servers = await AdminRepository.read_records('OrdersServerModel', filtration={'is_active': 'true'})
    for server in servers:
        if not data.get(f'active-{server.id}', None) or data.get(f'active-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с активными заказами для {server.name}')

        if not data.get(f'collected-{server.id}', None) or data.get(f'collected-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с полученными заказами для {server.name}')

    result = await refresh_orders_and_accounts(data, servers)

    return str(result)
