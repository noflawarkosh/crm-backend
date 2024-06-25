import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func

from admin.schemas import FileSchema
from admin.utils import generate_filename, s3_save, verify_file
from auth.models import UserSessionModel
from auth.router import authed
from database import DefaultRepository

from orgs.router import check_access
from products.models import ProductModel, ReviewModel, ProductSizeModel
from products.repository import ProductsRepository, ReviewsRepository
from products.schemas import ProductPOSTSchema, ProductReadSchema, ProductCreateSchema, ReviewCreateSchema, \
    ReviewReadSchema

from products.utils import parse_wildberries_card

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

    filename = generate_filename() if picture_data else None

    await ProductsRepository.create_product(
        {
            'org_id': organization.id,
            'wb_article': article,
            'wb_title': title,
            'status': 1,
            'media': filename + '.webp',
        },
        [size.model_dump() for size in sizes]
    )

    if picture_data:
        await s3_save(picture_data, filename, 'webp')


@router_products.get('/refresh')
async def refresh_product(product_id: int,
                          session: UserSessionModel = Depends(authed)):
    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_id, ProductModel.status != 3],
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
                    'barcode': None
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
        else:
            records.append(
                {
                    'id': current_size.id,
                    'wb_in_stock': True,
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

    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_id, ProductModel.status != 3],
        select_related=[ProductModel.sizes]
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    product = products[0]

    is_active = True
    for size in product.sizes:
        if not size.barcode:
            is_active = False
            break

    if is_active:
        await DefaultRepository.save_records([{'model': ProductModel, 'records': [{'id': product.id, 'status': 2}]}])
    else:
        await DefaultRepository.save_records([{'model': ProductModel, 'records': [{'id': product.id, 'status': 1}]}])


@router_products.get('/getOwned')
async def get_owned_products(org_id: int, session: UserSessionModel = Depends(authed)):

    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.org_id == org_id, ProductModel.status != 3],
        select_related=[ProductModel.sizes]
    )
    return [ProductReadSchema.model_validate(product, from_attributes=True) for product in products]


@router_products.post('/barcode')
async def create_barcode(size_id: int, barcode: str, session: UserSessionModel = Depends(authed)):
    sizes = await DefaultRepository.get_records(
        ProductSizeModel,
        filters=[ProductSizeModel.id == size_id],
        select_related=[ProductSizeModel.product]
    )

    if len(sizes) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    size = sizes[0]

    await check_access(size.product.org_id, session.user.id, 2)

    if size.barcode:
        raise HTTPException(status_code=403, detail=string_403)

    await DefaultRepository.save_records(
        [{'model': ProductSizeModel, 'records': [{'id': size_id, 'barcode': barcode}]}])

    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == size.product_id, ProductModel.status != 3],
        select_related=[ProductModel.sizes]
    )

    if len(sizes) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    product = products[0]

    is_active = True
    for size in product.sizes:
        if not size.barcode:
            is_active = False
            break

    if is_active:
        await DefaultRepository.save_records([{'model': ProductModel, 'records': [{'id': product.id, 'status': 2}]}])


@router_products.get('/disable')
async def disable_product(product_id: int,
                          session: UserSessionModel = Depends(authed)):
    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == product_id, ProductModel.status != 3],
    )

    if len(products) != 1:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    await check_access(products[0].org_id, session.user.id, 2)

    await DefaultRepository.save_records([{'model': ProductModel, 'records': [{'id': product_id, 'status': 3}]}])


@router_reviews.post('/create')
async def create_review(data: Annotated[ReviewCreateSchema, Depends()],
                        files: List[UploadFile] = File(...),
                        session: UserSessionModel = Depends(authed)
                        ):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail=string_product_too_many_files)

    products = await DefaultRepository.get_records(
        ProductModel,
        filters=[ProductModel.id == data.product_id, ProductModel.status != 3],
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
                FileSchema.model_validate(
                    {
                        'filename': file.filename,
                        'size': len(content),
                        'content': content,
                        'href': generate_filename()
                    }
                )
            )

    for file in ordered_files:
        try:
            await verify_file(file, ['image', 'video'])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{file.name}: {str(e)}")

    await ReviewsRepository.create_review(data, ordered_files)

    for file in ordered_files:
        await s3_save(file.content, file.href, file.name.rsplit('.', maxsplit=1)[1])


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
