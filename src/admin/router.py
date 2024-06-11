from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from datetime import datetime, timedelta
from admin.repository import AdminRepository
from admin.schemas import AdminReadSchema, AdminSessionCreateSchema

from auth.utils import hash_password, generate_token
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
    model = model + 'Model'
    params = request.query_params.__dict__['_dict']

    limit = params.get('limit', None)
    offset = params.get('offset', None)

    if limit:
        del params['limit']

    if offset:
        del params['offset']

    for key in params:
        if ',' in params[key]:
            params[key] = params[key].replace(' ', '').split(',')
        else:
            params[key] = [params[key]]

    data = await AdminRepository.read_records(model, filtration=params, limit=limit, offset=offset)

    if not data:
        raise HTTPException(status_code=404, detail=string_404)

    return [d.__dict__ for d in data]


@router.get('/fields/{model}')
async def reading_fields(model: str, admin: AdminReadSchema = Depends(authed)):
    data = await AdminRepository.read_fields(model + 'Model')
    if not data:
        raise HTTPException(status_code=404, detail=string_404)

    return data


@router.post('/save/{model}')
async def creating_data(model: str, request: Request, admin: AdminReadSchema = Depends(authed)):

    model = model + 'Model'
    model_fields = await AdminRepository.read_fields(model)

    values = dict(await request.form())

    typed_values = {}
    print(values)
    for field, value in values.items():
        if model_fields[field] == 'INTEGER':
            typed_values[field] = int(value) if value else None

        elif model_fields[field] == 'VARCHAR':
            typed_values[field] = str(value) if value else None

        elif model_fields[field] == 'BOOLEAN':
            typed_values[field] = True if value == 'true' else False

        elif model_fields[field] == 'DATETIME':
            typed_values[field] = datetime.fromisoformat(value) if value else None

        elif model_fields[field] == 'TIME':
            typed_values[field] = datetime.strptime(value, '%H:%M:%S').time() if value else None

        elif model_fields[field] == 'FLOAT':
            typed_values[field] = float(value) if value else None
    print(typed_values)
    record_id = typed_values.get('id', None)

    if record_id:
        del typed_values['id']
        await AdminRepository.update_record(model, record_id, typed_values)

    else:
        await AdminRepository.create_record(model, typed_values)

