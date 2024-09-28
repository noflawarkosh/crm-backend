from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import requests
from fastapi import APIRouter, Depends, Response, Request, HTTPException, UploadFile, File
from datetime import datetime, timedelta

from sqlalchemy import func, inspect
from starlette.responses import StreamingResponse

from admin.models import AdminSessionModel, AdminUserModel

from admin.utils import set_type, process_reviews_tasks_xlsx
from auth.models import UserModel, UserSessionModel
from orgs.repository import MembershipRepository
from payments.router import current_prices
from picker.models import PickerServerScheduleModel, PickerSettingsModel, PickerServerContractorModel, \
    PickerHistoryModel, PickerServerModel, PickerOrderStatus, PickerServerClientModel

from gutils import Strings
from database import Repository, AdminAuditLog
from orders.models import OrdersAddressModel, OrdersOrderModel, OrdersContractorModel, OrdersAccountModel, \
    OrderAddressStatusModel
from orgs.models import OrganizationModel, OrganizationMembershipModel
from payments.models import BalanceBillModel, BalanceSourceModel, BalancePricesModel, BalanceHistoryModel, \
    BalanceTargetModel, BalanceActionModel
from picker.utils import parse_excel_lines, detect_date
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
    'logs': (AdminAuditLog, 1048576, {}),
    'organizations': (OrganizationModel, 2048, {}),
    'organizations_full': (
        OrganizationModel, 2048,
        {
            'select_related': [OrganizationModel.owner, OrganizationModel.level, OrganizationModel.server],
            'filters': [OrganizationModel.status != 4]
        }
    ),
    'organizations_full_forced': (
        OrganizationModel, 2048,
        {
            'select_related': [OrganizationModel.owner, OrganizationModel.level, OrganizationModel.server],
        }
    ),
    'sizes': (ProductSizeModel, 64, {}),
    'actions': (BalanceActionModel, 256, {}),
    'orgs': (OrganizationModel, 2048, {}),
    'bills': (BalanceBillModel, 256, {}),
    'balance': (BalanceHistoryModel, 256, {}),
    'orders': (OrdersOrderModel, 16, {}),
    'addresses': (OrdersAddressModel, 4, {}),
    'accounts': (OrdersAccountModel, 32, {'select_related': [OrdersAccountModel.address, OrdersAccountModel.server]}),
    'addresses_full': (OrdersAddressModel, 256, {'select_related': [OrdersAddressModel.contractor]}),
    'products': (ProductModel, 64, {}),
    'reviews': (ReviewModel, 128, {}),
    'admins': (AdminUserModel, 16384, {}),
    'usersessions': (UserSessionModel, 65536, {}),
    'usersessions_full': (
        UserSessionModel, 65536,
        {
            'select_related': [UserSessionModel.user]
        }
    ),
    'adminsessions_full': (
        AdminSessionModel, 131072,
        {
            'select_related': [AdminSessionModel.admin]
        }
    ),
    'adminsessions': (AdminSessionModel, 131072, {}),
    'contractors': (OrdersContractorModel, 8, {}),
    'pickerstatuses': (PickerOrderStatus, 2, {}),
    'banks': (BalanceSourceModel, 1024, {}),
    'prices': (BalancePricesModel, 512, {}),
    'schedules': (PickerServerScheduleModel, 524288, {}),
    'servercontractors': (PickerServerContractorModel, 8, {}),
    'pickersettings': (PickerSettingsModel, 2, {}),
    'pickerhistory': (PickerHistoryModel, 2, {}),
    'levels': (BalancePricesModel, 2048, {}),
    'members': (OrganizationMembershipModel, 2048, {}),
    'sizes_full': (
        ProductSizeModel, 64,
        {
            'select_related': [ProductSizeModel.product],
            'deep_related': [
                [ProductSizeModel.product, ProductModel.organization]
            ]
        }
    ),

    'pickerorgs': (
        PickerServerClientModel, 2,
        {
            'select_related': [PickerServerClientModel.organization],
            'deep_related': [
                [PickerServerClientModel.organization, OrganizationModel.server],
            ]
        }
    ),

    'reviews_full': (
        ReviewModel, 128,
        {
            'select_related': [ReviewModel.size, ReviewModel.media],
            'deep_related': [
                [ReviewModel.size, ProductSizeModel.product],
                [ReviewModel.size, ProductSizeModel.product, ProductModel.organization],
            ]
        }
    ),
    'products_full': (
        ProductModel, 64,
        {
            'select_related': [ProductModel.sizes, ProductModel.organization]
        }
    ),
    'orders_full': (
        OrdersOrderModel, 16,
        {
            'select_related': [OrdersOrderModel.size, OrdersOrderModel.account],
            'deep_related': [
                [OrdersOrderModel.account, OrdersAccountModel.address],
                [OrdersOrderModel.size, ProductSizeModel.product],
                [OrdersOrderModel.size, ProductSizeModel.product, ProductModel.organization]
            ]
        }
    ),

    'servers': (
        PickerServerModel, 1,
        {
            'prefetch_related': [
                PickerServerModel.schedule,
                PickerServerModel.contractors,
            ],
            'order_by': [PickerServerModel.id.asc()]
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
    'address_statuses': (OrderAddressStatusModel, 4, {}),
    'express_reviews': (
        ReviewModel, 128,
        {
            'filters': [
                ReviewModel.is_express.is_(True),
                ReviewModel.status.in_([1, 2])
            ]
        }
    ),

}


async def every(request: Request = Request):
    token = request.cookies.get(cookies_admin_token_key)
    if not token:
        return None

    sessions = await Repository.get_records(
        AdminSessionModel,
        filters=[AdminSessionModel.token == token, AdminSessionModel.expires > func.now()],
        select_related=[AdminSessionModel.admin]
    )

    if len(sessions) != 1:
        return None

    session = sessions[0]

    if not session:
        return None

    if not session.admin.is_active:
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
    admin_check = await Repository.get_records(
        AdminUserModel,
        filters=[AdminUserModel.username == username.lower().replace(' ', '')]
    )

    if len(admin_check) != 1:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if Strings.hmac(password) != admin_check[0].password:
        raise HTTPException(status_code=403, detail=string_user_wrong_password)

    if not admin_check[0].is_active:
        raise HTTPException(status_code=403, detail=string_user_inactive_user)

    token = Strings.alphanumeric(256)
    await Repository.save_records([
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
    await Repository.save_records([
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
            if key == 'limit':
                if int(value) > 0:
                    kwargs['limit'] = int(value)
            else:
                field = getattr(model, key)
                filters.append(field == set_type(value, str(field.type)))

        if kwargs.get('filters', None):
            kwargs['filters'] = kwargs['filters'] + filters

        else:
            kwargs['filters'] = filters

    records = await Repository.get_records(model, **kwargs)

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
                    typed_value = Strings.hmac(str(typed_value))

                model_record_with_typed_values[field] = typed_value

            model_with_typed_records.append(model_record_with_typed_values)

        models_with_typed_records.append({
            'model': model,
            'records': model_with_typed_records
        })

    await Repository.save_records(models_with_typed_records, session_id=session.id, is_admin=True)


@router.delete('/delete/{section}/{record_id}')
async def reading_fields(section: str, record_id: int, session: AdminSessionModel = Depends(authed)):
    if not tables_access.get(section, None):
        raise HTTPException(status_code=404, detail=string_404)

    model, level, select_models = tables_access[section]

    if not level & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    await Repository.delete_record(model, record_id)


@router.post('/uploadBillMedia')
async def uploading_bill_media(bill_id: int, file: UploadFile = File(), session: AdminSessionModel = Depends(authed)):
    try:
        await Repository.verify_file(file, ['jpg', 'jpeg', 'png', 'webp', 'pdf', 'doc', 'docx', 'zip', 'rar'])

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")

    bills = await Repository.get_records(BalanceBillModel, filters=[BalanceBillModel.id == bill_id])

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    bill = bills[0]

    content = await file.read()
    n, t = await Repository.s3_autosave(content,
                                        f"{Strings.alphanumeric(32)}.{file.filename.rsplit('.', maxsplit=1)[1]}")

    record = {'id': bill.id, 'media': f'{n}.{t}'}

    if bill.status_id == 6:
        record['status_id'] = 3

    await Repository.save_records([
        {'model': BalanceBillModel, 'records': [record]}
    ])


@router.get("/xlsxReviewsTasks")
async def download_xlsx_reviews(type: int, session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    if type == 1:
        reviews = await Repository.get_records(
            ReviewModel,
            filters=[
                ReviewModel.status == 1,
                ReviewModel.strict_match.is_(False),
                ReviewModel.is_express.is_(False),
                ReviewModel.stars == 5
            ],
            select_related=[
                ReviewModel.media,
                ReviewModel.size
            ],
            filtration=[
                ReviewModel.media == None,
                OrganizationModel.is_competitor == False,
            ],
            joins=[
                ProductSizeModel,
                ProductModel,
                OrganizationModel
            ],
            deep_related=[
                [ReviewModel.size, ProductSizeModel.product],
                [ReviewModel.size, ProductSizeModel.product, ProductModel.organization]
            ]
        )

    elif type == 2:
        reviews = await Repository.get_records(
            ReviewModel,
            filters=[
                ReviewModel.status == 1,
                ReviewModel.strict_match.is_(False),
                ReviewModel.is_express.is_(False),
                ReviewModel.stars == 1
            ],
            select_related=[
                ReviewModel.media,
                ReviewModel.size
            ],
            filtration=[
                ReviewModel.media == None,
                OrganizationModel.is_competitor == True,
            ],
            joins=[
                ProductSizeModel,
                ProductModel,
                OrganizationModel
            ],
            deep_related=[
                [ReviewModel.size, ProductSizeModel.product],
                [ReviewModel.size, ProductSizeModel.product, ProductModel.organization]
            ]
        )

    else:
        raise HTTPException(status_code=403, detail=string_403)

    if len(reviews) == 0:
        raise HTTPException(status_code=415, detail=string_404)

    matches_ids = {
        0: '',
        1: 'Соответствует размеру',
        2: 'Маломерит',
        3: 'Большемерит'
    }

    tasks = {}
    revs_to_update = reviews
    for review in reviews:
        if tasks.get(review.size.product.wb_article):
            tasks[review.size.product.wb_article].append(review)
        else:
            tasks[review.size.product.wb_article] = [review]

    zip_file = BytesIO()
    with ZipFile(zip_file, 'w') as zip_archive:
        for article, reviews in tasks.items():
            excel_file = BytesIO()
            texts = []
            advs = []
            disadvs = []
            ids = []
            matches = []

            for review in reviews:
                texts.append(review.text if review.text else '')
                advs.append(review.advs if review.text else '')
                disadvs.append(review.disadvs if review.text else '')
                matches.append(matches_ids[review.match])
                ids.append(review.id)

            data = {
                "Достоинства": advs,
                "Недостатки": disadvs,
                "Комментарий к отзыву": texts,
                "Пол": [''] * len(texts),
                "Размер": [''] * len(texts),
                "Фото": [''] * len(texts),
                "": [''] * len(texts),
                " ": [''] * len(texts),
                "Видео": [''] * len(texts),
                "Соответствие размеру": matches,
                "Аккаунт": [''] * len(texts),
                "Статус": [''] * len(texts),
                "Результат": [''] * len(texts),
                "Системный ID": ids
            }

            df = pd.DataFrame(data)
            df.to_excel(excel_file, index=False, sheet_name=article)
            excel_file.seek(0)
            zip_archive.writestr(f"{article}.xlsx", excel_file.getvalue())

    zip_file.seek(0)

    headers = {
        'Content-Disposition': f'attachment; filename=tasks.zip'
    }

    await Repository.save_records(
        [
            {
                'model': ReviewModel,
                'records': [{'id': review.id, 'status': 2} for review in revs_to_update]
            }
        ]
    )

    return StreamingResponse(zip_file, media_type='application/zip', headers=headers)













@router.post('/xlsxReviewsTasksPay')
async def get_reviews_of_organization(file: UploadFile = File(...), session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    try:
        await Repository.verify_file(file, ['xlsx'])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")

    try:
        await process_reviews_tasks_xlsx(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")


@router.post('/updateReviewStatus')
async def update_review_status(review_id: int, status: int, session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    reviews = await Repository.get_records(
        ReviewModel,
        filters=[
            ReviewModel.id == review_id
        ]
    )

    if len(reviews) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    review = reviews[0]

    if status not in [2, 4]:
        raise HTTPException(status_code=400, detail=string_400)

    if status == 2 and review.status != 1:
        raise HTTPException(status_code=400, detail=string_400)

    if status == 4 and review.status not in [1, 2]:
        raise HTTPException(status_code=400, detail=string_400)

    await Repository.save_records(
        [
            {
                'model': ReviewModel,
                'records': [{'id': review.id, 'status': status}]
            }
        ]
    )


@router.post('/payReview')
async def update_review_status(review_id: int, session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    reviews = await Repository.get_records(
        ReviewModel,
        filters=[
            ReviewModel.id == review_id
        ],
        select_related=[ReviewModel.media, ReviewModel.size],
        deep_related=[
            [ReviewModel.size, ProductSizeModel.product],
            [ReviewModel.size, ProductSizeModel.product, ProductModel.organization]
        ]
    )

    if len(reviews) != 1:
        raise HTTPException(status_code=404, detail=string_404)
    review = reviews[0]

    if review.status != 2:
        raise HTTPException(status_code=400, detail=string_400)

    level, purchases = await current_prices(review.size.product.organization)

    price = level.price_review
    target_id = 7

    if review.media:
        price = level.price_review_media
        target_id = 5

    if review.strict_match is True:
        price = level.price_review_request
        target_id = 6

    if review.is_express is True:
        price = level.price_review_request
        target_id = 6

    await Repository.save_records(
        [
            {
                'model': ReviewModel,
                'records': [
                    {
                        'id': review.id,
                        'status': 3
                    }
                ]
            },
            {
                'model': BalanceHistoryModel,
                'records': [
                    {
                        'amount': price,
                        'org_id': review.size.product.organization.id,
                        'target_id': target_id,
                        'record_id': review.id,
                        'action_id': 3
                    }
                ]
            }
        ]
    )

    target = await Repository.get_records(BalanceTargetModel, filters=[BalanceTargetModel.id == target_id])

    return f'{target[0].title} ({price} руб.)'


@router.get('/getPaymentsDetails')
async def create_organization(org_id: int, start: datetime, end: datetime,
                              session: AdminSessionModel = Depends(authed)):
    if not 2048 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

    history = await Repository.get_records(
        BalanceHistoryModel,
        filters=[
            BalanceHistoryModel.org_id == org_id,
            BalanceHistoryModel.date >= start,
            BalanceHistoryModel.date <= end,
        ]
    )

    return [record.__dict__ for record in history]


@router.get('/get_managers')
async def create_organization(org_id: int, session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    records = await MembershipRepository.read_memberships_of_organization(org_id)

    return [record.__dict__ for record in records]


@router.get('/getAccess')
async def create_organization(org_id: int, session: AdminSessionModel = Depends(authed)):
    if not 128 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    records = await MembershipRepository.read_memberships_of_organization(org_id)

    return [record.__dict__ for record in records]


@router.get('/getBalance')
async def create_organization(org_id: int = None, session: AdminSessionModel = Depends(authed)):
    if not 2048 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    query = 'SELECT SUM(' \
            'CASE ' \
            'WHEN action_id IN (1, 4) THEN amount ' \
            'WHEN action_id IN (2, 3) THEN -amount ' \
            'ELSE 0 ' \
            'END) AS total_amount ' \
            'FROM balance_history '

    if org_id is not None:

        try:
            int(org_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=string_400)

        query += f'WHERE org_id = {org_id};'

    result = await Repository.execute_sql(query)

    return result[0][0]


@router.get('/getBalances')
async def create_organization(session: AdminSessionModel = Depends(authed)):
    if not 2048 & session.admin.level:
        raise HTTPException(status_code=403, detail=string_403)

    query = 'SELECT org_id,' \
            'SUM(' \
            'CASE ' \
            'WHEN action_id IN (1, 4) THEN amount ' \
            'WHEN action_id IN (2, 3) THEN -amount ' \
            'ELSE 0 ' \
            'END) AS balance ' \
            'FROM balance_history ' \
            'GROUP BY org_id;'

    result = await Repository.execute_sql(query)

    return {x[0]: x[1] for x in result}


@router.post('/approve')
async def approve(result: bool, record_table: str, record_id: int, session: AdminSessionModel = Depends(authed)):

    if record_table == 'bill':
        bills = await Repository.get_records(
            BalanceBillModel,
            filters=[BalanceBillModel.id == record_id],
            select_related=[BalanceBillModel.status]
        )

        if len(bills) != 1:
            return {'detail': '✅⚠️ Счет не найден', 'remove_markup': False}

        bill = bills[0]

        if bill.status_id != 2:
            return {'detail': f'✅⚠️ Заявка уже рассмотрена: {bill.status.title}', 'remove_markup': True}

        records = [{'model': BalanceBillModel, 'records': [{'id': bill.id, 'status_id': 1 if result else 5}]}]

        if result is True:
            records.append({'model': BalanceHistoryModel, 'records': [
                {
                    'amount': bill.amount,
                    'org_id': bill.org_id,
                    'description': 'Пополнение по счету #' + str(bill.id),
                    'action_id': 1,
                }
            ]})

        await Repository.save_records(records)

        if result is True:
            return {'detail': '✅🟢 Счет успешно одобрен', 'remove_markup': True}
        else:
            return {'detail': '✅🔴 Счет успешно отклонен', 'remove_markup': True}


async def force_save_product(wb_article, wb_title, sizes, org_id):
    wb_url = f'https://www.wildberries.ru/catalog/{wb_article}/detail.aspx'

    title, p_article, sizes, picture_data = parse_wildberries_card(wb_url)

    filename = Strings.alphanumeric(32) if picture_data else None

    await ProductsRepository.create_product(
        {
            'org_id': int(org_id),
            'wb_article': p_article,
            'wb_title': title,
            'status': 1,
            'media': filename + '.webp',
        },
        [size.model_dump() for size in sizes]
    )

    if picture_data:
        await Repository.s3_save_image(picture_data, filename + '.webp')

    return True
    """
    except Exception as e:

        await ProductsRepository.create_product(
            {
                'org_id': int(org_id),
                'wb_article': wb_article,
                'wb_title': wb_title,
                'status': 1,
            },
            [{
                'wb_size_origName': wb_size_origName,
                'wb_size_optionId': wb_size_optionId,
                'wb_in_stock': False,
                'wb_price': None,
                'barcode': None,
                'is_active': True,
            }]
        )

        return False
"""


@router.post('/x')
async def x(file: UploadFile = File(...)):
    db_orgs = await Repository.get_records(OrganizationModel)
    df_orgs = pd.DataFrame([{'id': x.id, 'title': x.title} for x in db_orgs])

    columns = {
        'title': 0,
        'balance': 1,
    }

    content = await file.read()

    data = await parse_excel_lines(pd.read_excel(BytesIO(content), dtype=str).values.tolist(), columns)
    tt = 0
    actions = []
    for line in data:

        aid = None
        bal = int(line['balance'])
        abal = abs(bal)

        if bal == 0:
            continue

        if bal > 0:
            tt += abal
            aid = 1

        elif bal < 0:
            tt -= abal
            aid = 3

        query = df_orgs.query(f"title == '{line['title']}'")
        org_id = query['id'].iloc[0] if len(query.values) != 0 else None

        actions.append({
            'amount': abal,
            'org_id': int(org_id),
            'action_id': aid,
            'description': 'Стартовый баланс',
        })

    await Repository.save_records([{'model': BalanceHistoryModel, 'records': actions}])

    return
    # Caching data from db
    db_accounts = await Repository.get_records(OrdersAccountModel)
    db_prods = await Repository.get_records(ProductModel, select_related=[ProductModel.sizes])
    db_orgs = await Repository.get_records(OrganizationModel)
    db_statuses = await Repository.get_records(PickerOrderStatus)

    df_accounts = pd.DataFrame([{'id': x.id, 'number': x.number} for x in db_accounts])
    df_orgs = pd.DataFrame([{'id': x.id, 'title': x.title} for x in db_orgs])

    columns = {
        'address': 0,
        'status': 1,
        'account_name': 2,
        'telnum': 3,
        'collect_code': 4,
        'organization_title': 5,
        'product_article': 6,
        'product_size': 7,
        'product_title': 8,
        'price': 9,
        'dt_ordered': 10,
        'dt_delivered': 11,
        'dt_collected': 12,
        'account_number': 13,
        'uuid': 14,
    }

    content = await file.read()

    data = await parse_excel_lines(pd.read_excel(BytesIO(content), dtype=str).values.tolist(), columns)

    processed_accounts = []
    orders_to_db = []
    pnf = []
    prods_to_parse = {}
    for line in reversed(data):

        size_id = None
        account_id = None
        status_id = None
        status = None

        # SEARCH STATUS
        status_model = None
        for db_status in db_statuses:
            if db_status.full_match and line['status'] == db_status.title:
                status_model = db_status
                status_id = db_status.id
                status = status_model.status_number
                break
            elif not db_status.full_match and db_status.title in line['status']:
                status_model = db_status
                status_id = db_status.id
                status = status_model.status_number
                break

        # SEARCH ORG
        query = df_orgs.query(f"title == '{line['organization_title']}'")
        org_id = query['id'].iloc[0] if len(query.values) != 0 else None

        # SEARCH SIZE
        for prod in db_prods:
            found = False

            if prod.wb_article == line['product_article'] and prod.org_id == org_id:
                for size in prod.sizes:

                    if size.wb_size_origName == line['product_size'] or size.wb_size_name == line['product_size']:
                        size_id = size.id
                        found = True
                        break

                if not found:
                    size_id = prod.sizes[0].id

            if found:
                break

        # SEARCH ACCOUNT
        query = df_accounts.query(f"number == '{line['account_number']}'")
        account_id = query['id'].iloc[0] if len(query.values) != 0 else None

        if not size_id or not account_id or not status_id or not status:
            print(
                {
                    'size_id': size_id,
                    'account_id': account_id,
                    'picker_status_id': status_id,
                    'status': status,
                    'line': line['line_number']
                }
            )
            raise HTTPException(status_code=404, detail='NOT FULL')

        # ADD TO DB
        orders_to_db.append({
            'wb_keyword': line['product_title'],
            'wb_price': int(line['price']),
            'wb_uuid': line['uuid'],
            'wb_status': line['status'],
            'wb_collect_code': line['collect_code'],

            'description': 'forced',
            'dt_planed': detect_date(line['dt_ordered']),
            'dt_ordered': detect_date(line['dt_ordered']),
            'dt_delivered': detect_date(line['dt_delivered']),
            'dt_collected': detect_date(line['dt_collected']),

            'size_id': size_id,
            'account_id': account_id,
            'picker_status_id': status_id,
            'status': status,
        })

    await Repository.save_records([{'model': OrdersOrderModel, 'records': orders_to_db}])
    return

    # Barcodes
    content = await file.read()
    columns = {
        'inn': 0,
        'art': 1,
        'bar': 2,
        'sze': 3,
        'ttl': 4
    }

    data = await parse_excel_lines(pd.read_excel(BytesIO(content), dtype=str).values.tolist(), columns)

    db_prods = await Repository.get_records(ProductModel, select_related=[ProductModel.sizes])

    bs_to = []
    for line in data:

        bar = line['bar'].replace('БАР', '').replace(' ', '')
        art = line['art'].replace(' ', '').replace('АРТ', '')
        sze = line['sze'].replace('>>', '')

        for prod in db_prods:
            found = False
            if prod.wb_article == art:

                for size in prod.sizes:

                    if size.wb_size_origName == sze:
                        bs_to.append({
                            'id': size.id,
                            'barcode': bar,
                        })
                        found = True
                        break
            if found:
                break

    await Repository.save_records([{'model': ProductSizeModel, 'records': bs_to}])
    return

    # PRODS
    content = await file.read()
    columns = {
        'inn': 0,
        'art': 1,
        'bar': 2,
        'sze': 3,
        'ttl': 4
    }

    data = await parse_excel_lines(pd.read_excel(BytesIO(content), dtype=str).values.tolist(), columns)

    db_orgs = await Repository.get_records(OrganizationModel)
    df_orgs = pd.DataFrame(
        [
            {
                'id': x.id,
                'inn': x.inn,
            }
            for x in db_orgs
        ]
    )

    prods_to_parse = {}

    for line in data:

        query = df_orgs.query(f"inn == '{line['inn'].replace(' ', '').replace('ИНН', '')}'")
        org_id = query['id'].iloc[0] if len(query.values) != 0 else None

        if not org_id:
            raise HTTPException(status_code=400, detail=line['inn'])

        art = line['art'].replace(' ', '').replace('АРТ', '')
        ttl = line['ttl']
        sze = line['sze'].replace('>>', '')
        org_id = str(org_id)
        if sze == '':
            sze = None

        if prods_to_parse.get(org_id):
            if prods_to_parse[org_id].get(art):
                prods_to_parse[org_id][art]['sizes'].append(
                    {
                        'wb_size_origName': sze,
                        'wb_size_optionId': line['line_number'],
                        'wb_in_stock': False,
                        'wb_price': None,
                        'barcode': None,
                        'is_active': True,
                    }
                )
            else:
                prods_to_parse[org_id][art] = {
                    'product': {
                        'org_id': int(org_id),
                        'wb_article': art,
                        'wb_title': ttl,
                        'status': 1,
                    },
                    'sizes': [
                        {
                            'wb_size_origName': sze,
                            'wb_size_optionId': line['line_number'],
                            'wb_in_stock': False,
                            'wb_price': None,
                            'barcode': None,
                            'is_active': True,
                        }
                    ]
                }
        else:
            prods_to_parse[org_id] = {}
            prods_to_parse[org_id][art] = {
                'product': {
                    'org_id': int(org_id),
                    'wb_article': art,
                    'wb_title': ttl,
                    'status': 1,
                },
                'sizes': [
                    {
                        'wb_size_origName': sze,
                        'wb_size_optionId': line['line_number'],
                        'wb_in_stock': False,
                        'wb_price': None,
                        'barcode': None,
                        'is_active': True,
                    }
                ]
            }

    for org_id in prods_to_parse:
        for art in prods_to_parse[org_id]:
            print(org_id, art, end='')
            try:
                wb_url = f'https://www.wildberries.ru/catalog/{art}/detail.aspx'

                title, p_article, sizes, picture_data = parse_wildberries_card(wb_url)

                filename = Strings.alphanumeric(32) if picture_data else None

                await ProductsRepository.create_product(
                    {
                        'org_id': int(org_id),
                        'wb_article': p_article,
                        'wb_title': title,
                        'status': 1,
                        'media': filename + '.webp',
                    },
                    [size.model_dump() for size in sizes]
                )

                if picture_data:
                    await Repository.s3_save_image(picture_data, filename + '.webp')

                print('WB')

            except Exception as e:
                print('FORCED', str(e))
                await ProductsRepository.create_product(
                    prods_to_parse[org_id][art]['product'],
                    prods_to_parse[org_id][art]['sizes']
                )

    return prods_to_parse
    rr = await force_save_product(
        line['art'].replace(' ', '').replace('ИНН', ''),
        line['ttl'],
        line['sze'].replace('>>', ''),
        line['line_number'],
        org_id
    )

    print(line['line_number'], len(data), org_id, rr)

    return
    a = []
    for x in range(11):
        p = Strings.alphanumeric(10)

        a.append([
            {
                'u': 'wb_' + Strings.alphanumeric(8).lower(),
                'p': p,
                'h': Strings.hmac(p)
            }
        ])
    return a
    content = await file.read()
    columns = {
        'is_competitor': 1,
        'title': 2,
        'inn': 4,
        'owner_tg': 7,
        'owner_name': 8,
    }

    data = await parse_excel_lines(pd.read_excel(BytesIO(content), dtype=str).values.tolist(), columns)

    db_users = await Repository.get_records(UserModel)
    df_users = pd.DataFrame(
        [
            {
                'id': x.id,
                'telegram': x.telegram,
            }
            for x in db_users
        ]
    )

    orgs = []
    logs = []

    for line in data:
        query = df_users.query(f"telegram == '{line['owner_tg'].replace('@', '')}'")
        user_id = query['id'].iloc[0] if len(query.values) != 0 else None

        if not user_id:
            logs.append(line)
            continue

        orgs.append(
            {
                'title': line['title'],
                'inn': line['inn'].replace(' ', '').replace('ИНН', ''),
                'status': 2,
                'is_competitor': True if line['is_competitor'] == '1' else False,
                'owner_id': user_id,
                'server_id': 11,

            }
        )

    await Repository.save_records([{'model': OrganizationModel, 'records': orgs}])

    return logs


# Forced saves
"""
async def force_save_product(wb_article, wb_title, wb_size_origName, wb_size_optionId, org_id):
    try:
        wb_url = f'https://www.wildberries.ru/catalog/{wb_article}/detail.aspx'

        title, p_article, sizes, picture_data = parse_wildberries_card(wb_url)

        filename = generate_filename() if picture_data else None

        await ProductsRepository.create_product(
            {
                'org_id': int(org_id),
                'wb_article': wb_article,
                'wb_title': wb_title,
                'status': 1,
                'media': filename + '.webp',
            },
            [size.model_dump() for size in sizes]
        )

        if picture_data:
            await s3_save(picture_data, filename, 'webp')

        return True

    except Exception as e:

        await ProductsRepository.create_product(
            {
                'org_id': int(org_id),
                'wb_article': wb_article,
                'wb_title': wb_title,
                'status': 1,
            },
            [{
                'wb_size_origName': wb_size_origName,
                'wb_size_optionId': wb_size_optionId,
                'wb_in_stock': False,
                'wb_price': None,
                'barcode': None,
                'is_active': True,
            }]
        )

        return False


async def force_save_order(x):
    db_sizes = await DefaultRepository.get_records(ProductSizeModel)
    db_products = await DefaultRepository.get_records(ProductModel)
    db_organizations = await DefaultRepository.get_records(OrganizationModel)

    df_products = pd.DataFrame([{'id': x.id, 'org_id': x.org_id, 'article': x.wb_article} for x in db_products])
    df_organizations = pd.DataFrame([{'id': x.id, 'title': x.title} for x in db_organizations])
    df_sizes = pd.DataFrame([{'id': x.id, 'product_id': x.product_id, 'wb_size_origName': x.wb_size_origName,
                              'wb_size_name': x.wb_size_name} for x in db_sizes])
    for xx in x:
        if force_save:

            query = df_organizations.query(f"title == '{line['organization_title']}'")
            organization_id = query['id'].iloc[0] if len(query.values) != 0 else None

            if not organization_id:
                logs_orders.append(
                    {
                        'target': line['order_uuid'],
                        'success': False,
                        'detail': 'Организация не найдена',
                        'value': line['organization_title'],
                        'line': line['line_number'],
                        'orders_type': orders_type,
                        'server': server.name,
                    }
                )
                continue

            query = df_products.query(f"article == '{line['product_article']}'")
            product_id = query['id'].iloc[0] if len(query.values) != 0 else None

            if not product_id:
                logs_orders.append(
                    {
                        'target': line['order_uuid'],
                        'success': False,
                        'detail': f'Товар не найден в списке товаров {line["organization_title"]}',
                        'value': line['product_article'],
                        'line': line['line_number'],
                        'orders_type': orders_type,
                        'server': server.name,
                    }
                )
                continue

            query = df_sizes.query(f'product_id == {product_id}')

            if len(query) == 0:
                logs_orders.append(
                    {
                        'target': line['order_uuid'],
                        'success': False,
                        'detail': f'Размеры товара не найдены',
                        'value': line['product_article'],
                        'line': line['line_number'],
                        'orders_type': orders_type,
                        'server': server.name,
                    }
                )
                continue

            size_id = query['id'].iloc[0]

            if len(query) != 1:
                for i, row in query.iterrows():
                    if (row['wb_size_origName'] == line['product_size'] or
                            row['wb_size_name'] == line['product_size']):
                        size_id = row['id']
                        break

            data_orders_to_db.append(
                {
                    'wb_keyword': line['product_title'],
                    'wb_price': int(line['price']),
                    'wb_uuid': line['order_uuid'],
                    'wb_status': line['status'],
                    'wb_collect_code': line['collect_code'],

                    'status': 3,
                    'description': 'forced',

                    'dt_planed': detect_date(line['dt_ordered']),
                    'dt_ordered': detect_date(line['dt_ordered']),
                    'dt_delivered': detect_date(line['dt_delivered']),
                    'dt_collected': detect_date(line['dt_collected']),

                    'size_id': int(size_id),
                    'account_id': int(account_id)
                }
            )

            logs_orders.append(
                {
                    'target': line['order_uuid'],
                    'success': True,
                    'detail': 'Заказ сохранен методом ForceSave',
                    'value': line['order_uuid'],
                    'line': line['line_number'],
                    'orders_type': orders_type,
                    'server': server.name,
                }
            )
            continue

"""
