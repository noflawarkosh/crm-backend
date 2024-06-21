import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func

from auth.models import UserSessionModel
from auth.router import authed
from database import DefaultRepository

from orgs.router import check_access
from products.models import ProductModel, ReviewModel, ProductSizeModel
from products.repository import ProductsRepository, ReviewsRepository
from products.schemas import ProductPOSTSchema, ProductReadSchema, ProductCreateSchema, ReviewCreateSchema, \
    ReviewReadSchema

from products.utils import parse_wildberries_card

from storage.schemas import StoragePOSTSchema, StorageFileSchema
from storage.utils import autosave_file, generate_filename, verify_file
from strings import *

router_products = APIRouter(
    prefix="/products",
    tags=["Products"]
)

router_reviews = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)


@router_products.post('/create')
async def create_product(data: Annotated[ProductPOSTSchema, Depends()], session: UserSessionModel = Depends(authed)):
    organization, membership = await check_access(data.org_id, session.user.id, 2)

    try:
        title, article, sizes, picture_data = parse_wildberries_card(data.wb_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    product_record = await ProductsRepository.create_product(
        ProductCreateSchema.model_validate(
            {
                'org_id': organization.id,
                'barcode': data.barcode,
                'wb_article': article,
                'wb_title': title,
            }
        ),
        sizes,
        StoragePOSTSchema.model_validate(
            {
                'title': title,
                'description': None,
                'storage_href': generate_filename() + '.webp',
                'type': 'webp',
                'owner_id': session.user.id
            }
        ) if picture_data else None
    )

    if not product_record:
        raise HTTPException(status_code=500, detail=string_500)

    new_product = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_record.id],
        select_related=[ProductModel.media, ProductModel.sizes]
    )

    await autosave_file(new_product[0].media.storage_href, picture_data)


@router_products.get('/refresh')
async def refresh_product(product_id: int,
                          session: UserSessionModel = Depends(authed)):
    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_id, ProductModel.is_active],
        select_related=[ProductModel.sizes]
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    await check_access(products[0].org_id, session.user.id, 2)

    if products[0].last_update + datetime.timedelta(minutes=5) > datetime.datetime.now():
        remaining = (products[0].last_update + datetime.timedelta(minutes=5)) - datetime.datetime.now()

        raise HTTPException(
            status_code=403,
            detail=string_product_refresh_error + f'. Вы сможете обновить этот товар через {remaining}'
        )

    try:
        title, article, sizes, picture_data = parse_wildberries_card(
            f'https://www.wildberries.ru/catalog/{products[0].wb_article}/detail.aspx'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    current_sizes = products[0].sizes
    new_sizes = sizes

    records = []

    for new_size in new_sizes:
        found = False
        for current_size in current_sizes:
            if new_size.wb_size_optionId == current_size.wb_size_optionId:
                records.append(
                    {
                        'id': current_size.id,
                        'wb_size_name': new_size.wb_size_name,
                        'wb_size_origName': new_size.wb_size_origName,
                        'wb_in_stock': new_size.wb_in_stock,
                        'wb_price': new_size.wb_price,
                    }
                )
                found = True
                break

        if not found:
            records.append(
                {
                    'wb_size_optionId': new_size.wb_size_optionId,
                    'wb_size_name': new_size.wb_size_name,
                    'wb_size_origName': new_size.wb_size_origName,
                    'wb_in_stock': new_size.wb_in_stock,
                    'wb_price': new_size.wb_price,
                    'product_id': products[0].id,
                }
            )

    for current_size in current_sizes:
        found = False

        for new_size in new_sizes:
            if current_size.wb_size_optionId == new_size.wb_size_optionId:
                found = True
                break

        if not found:
            records.append(
                {
                    'id': current_size.id,
                    'wb_in_stock': False,
                }
            )

    await DefaultRepository.save_records(
        [
            {'model': ProductSizeModel, 'records': records},
            {'model': ProductModel, 'records': [
                {
                    'id': products[0].id,
                    'last_update': func.now(),
                    'wb_article': article,
                    'wb_title': title,
                }
            ]}
        ]

    )

    await check_access(products[0].org_id, session.user.id, 2)


@router_products.get('/getOwned')
async def get_owned_products(org_id: int, session: UserSessionModel = Depends(authed)):
    await check_access(org_id, session.user.id, 2)
    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.org_id == org_id, ProductModel.is_active],
        select_related=[ProductModel.media, ProductModel.sizes]
    )
    return [ProductReadSchema.model_validate(product, from_attributes=True) for product in products]


@router_products.get('/disable')
async def disable_product(product_id: int,
                          session: UserSessionModel = Depends(authed)):
    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_id, ProductModel.is_active],
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    await check_access(products[0].org_id, session.user.id, 2)

    await DefaultRepository.save_records([{'model': ProductModel, 'records': [{'id': product_id, 'is_active': False}]}])


@router_reviews.post('/create')
async def create_review(data: Annotated[ReviewCreateSchema, Depends()],
                        files: List[UploadFile] = File(...),
                        session: UserSessionModel = Depends(authed)
                        ):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail=string_product_too_many_files)

    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == data.product_id, ProductModel.is_active],
        select_related=[ProductModel.sizes]
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    await check_access(products[0].org_id, session.user.id, 8)

    if data.size_id and data.size_id not in [size.id for size in products[0].sizes]:
        raise HTTPException(status_code=400, detail=string_403)

    if data.match:
        if not data.size_id:
            raise HTTPException(status_code=400, detail=string_product_size_not_selected_but_match)

        if data.match not in [1, 2, 3]:
            raise HTTPException(status_code=404, detail=string_404)

    ordered_files = []
    for file in files:
        if file.size > 0:
            content = await file.read()
            ordered_files.append(
                StorageFileSchema.model_validate(
                    {
                        'name': file.filename,
                        'size': len(content),
                        'content': content,
                        'href': generate_filename()
                    }
                )
            )

    for file in ordered_files:
        try:
            await verify_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{file.name}: {str(e)}")

    media_schemas = []

    for file in ordered_files:
        media_schemas.append(StoragePOSTSchema.model_validate(
            {
                'title': file.name,
                'description': None,
                'storage_href': file.href + f".{file.name.rsplit('.', maxsplit=1)[1]}",
                'type': file.name.rsplit('.', maxsplit=1)[1],
                'owner_id': session.user.id
            }
        ))

    review_record = await ReviewsRepository.create_review(data, media_schemas)

    if not review_record:
        raise HTTPException(status_code=500, detail=string_500)

    for file in ordered_files:
        await autosave_file(file.href + f".{file.name.rsplit('.', maxsplit=1)[1]}", file.content)


@router_reviews.get('/getOwned')
async def get_reviews_of_organization(org_id: int, session: UserSessionModel = Depends(authed)
                                      ) -> list[ReviewReadSchema]:
    await check_access(org_id, session.user.id, 8)
    reviews = await ReviewsRepository.get_owned_by_org_id(org_id)
    return [ReviewReadSchema.model_validate(record, from_attributes=True) for record in reviews]


@router_reviews.get('/disable')
async def disable_review(review_id: int,
                         session: UserSessionModel = Depends(authed)):
    reviews = await DefaultRepository.get_records(
        ReviewModel,
        filters=[ReviewModel.id == review_id],
        select_related=[ReviewModel.product]
    )

    if len(reviews) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    await check_access(reviews[0].product.org_id, session.user.id, 8)

    await DefaultRepository.save_records([{'model': ReviewModel, 'records': [{'id': review_id, 'status': 4}]}])
