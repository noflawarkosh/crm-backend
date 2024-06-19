import json
import urllib
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException, UploadFile, File
from datetime import datetime, timedelta
from admin.repository import AdminRepository
from admin.schemas import AdminReadSchema, AdminSessionCreateSchema

from auth.utils import hash_password, generate_token
from database import DefaultRepository
from strings import *
from inspect import iscoroutinefunction
from typing import Any

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


async def get_admin(request):
    token = request.cookies.get(cookies_admin_token_key)

    if not token:
        return None

    session = await AdminRepository.read_session(token)

    if not session:
        return None

    if session.ip != request.client.host or session.user_agent != request.headers.get('user-agent'):
        return None

    admin = await AdminRepository.read_admin_by_token(token)

    return admin


async def authed(request: Request = Request):
    result = await get_admin(request)

    if result:
        return result
    else:
        raise HTTPException(status_code=401, detail=string_401)


async def not_authed(request: Request = Request):
    result = await get_admin(request)

    if result:
        raise HTTPException(status_code=409, detail=string_400_already_authed)
    else:
        return result


async def every(request: Request = Request):
    result = await get_admin(request)
    return result


@router.post('/login')
async def login(request: Request, response: Response, username: str, password: str,
                admin: AdminReadSchema = Depends(not_authed)):
    admin_check = await AdminRepository.read_admin_by_attribute('username', username.lower().replace(' ', ''), True)

    if not admin_check:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if hash_password(password) != admin_check.password:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    admin_session = await AdminRepository.create_session(
        AdminSessionCreateSchema.model_validate(
            {
                'user_id': admin_check.id,
                'token': generate_token(256),
                'user_agent': request.headers.get('user-agent'),
                'ip': request.client.host,
                'expires': datetime.now() + timedelta(days=3)
            }
        )
    )

    response.set_cookie(key=cookies_admin_token_key, value=admin_session.token)


@router.get('/logout')
async def logout(request: Request, response: Response, admin: AdminReadSchema = Depends(authed)):
    await AdminRepository.update_deactivate_session(request.cookies.get(cookies_admin_token_key))
    response.delete_cookie(cookies_admin_token_key)


@router.get('/get/{model}')
async def reading_data(model: str, request: Request, admin: AdminReadSchema = Depends(authed)):
    model = await AdminRepository.read_model(model + 'Model')
    params = request.query_params.__dict__['_dict']

    for key in params:
        if ',' in params[key]:
            params[key] = params[key].replace(' ', '').split(',')
        else:
            params[key] = [params[key]]

    data = await DefaultRepository.get_records(model, filters=params)

    return [d.__dict__ for d in data]


@router.get('/fields/{model}')
async def reading_fields(model: str, admin: AdminReadSchema = Depends(authed)):
    data = await AdminRepository.read_fields(model + 'Model')

    if not data:
        raise HTTPException(status_code=404, detail=string_404)

    return data


@router.post('/save')
async def creating_data(data: dict[str, list[dict]], request: Request, admin: AdminReadSchema = Depends(authed)):
    models_with_typed_records = {}

    for model in data:

        model_fields = await AdminRepository.read_fields(model + 'Model')
        model_with_typed_records = []

        for record in data[model]:

            model_record_with_typed_values = {}

            for field, value in record.items():
                if model_fields[field] == 'INTEGER':
                    model_record_with_typed_values[field] = int(value) if value else None

                elif model_fields[field] == 'VARCHAR':
                    model_record_with_typed_values[field] = str(value) if value else None

                elif model_fields[field] == 'BOOLEAN':
                    model_record_with_typed_values[field] = bool(value)

                elif model_fields[field] == 'DATETIME':
                    model_record_with_typed_values[field] = \
                        datetime.fromisoformat(value) if value else None

                elif model_fields[field] == 'TIME':
                    model_record_with_typed_values[field] = \
                        datetime.strptime(value, '%H:%M:%S').time() if value else None

                elif model_fields[field] == 'FLOAT':
                    model_record_with_typed_values[field] = float(value) if value else None

                if field == 'password':
                    model_record_with_typed_values[field] = hash_password(value)

            model_with_typed_records.append(model_record_with_typed_values)
        models_with_typed_records[model + 'Model'] = model_with_typed_records

    await AdminRepository.save_records(models_with_typed_records)


@router.delete('/delete/{model}/{record_id}')
async def reading_fields(model: str, record_id: int, admin: AdminReadSchema = Depends(authed)):
    await AdminRepository.delete_record(model + 'Model', record_id)


@router.post('/test')
async def test(request: Request, admin: AdminReadSchema = Depends(authed)):
    data = dict(await request.form())

    servers = await AdminRepository.read_records('OrdersServerModel', filtration={'is_active': 'true'})
    for server in servers:
        if not data.get(f'active-{server.id}', None) or data.get(f'active-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с активными заказами для {server.name}')

        if not data.get(f'collected-{server.id}', None) or data.get(f'collected-{server.id}') == 'undefined':
            raise HTTPException(status_code=400, detail=f'Отсутствует файл с полученными заказами для {server.name}')

    result = await refresh_orders_and_accounts(data, servers)

    return str(result)
