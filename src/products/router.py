from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from auth.models import UserModel
from auth.router import authed
from orgs.repository import OrganizationRepository, MembershipRepository
from orgs.utils import check_access
from products.repository import ProductsRepository, ReviewsRepository
from products.schemas import ProductPOSTSchema, ProductGETSchema, ProductInsertSchema, ProductSizeInsertSchema, \
    ReviewPOSTSchema, ReviewGETSchema, ProductNonRelGETSchema

from products.utils import parse_wildberries_card
from storage.repository import StorageRepository
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
async def create_product(data: Annotated[ProductPOSTSchema, Depends()],
                         user: UserModel = Depends(authed)
                         ) -> ProductGETSchema:
    data_dict = data.model_dump()

    try:
        organization, membership = await check_access(data_dict.get('org_id'), user.id, 2)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        title, article, sizes, picture_data = parse_wildberries_card(data_dict.get('wb_url'))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    product_record = await ProductsRepository.add_one(
        ProductInsertSchema.model_validate(
            {
                'org_id': organization.id,
                'barcode': data_dict.get('barcode'),
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
                'owner_id': user.id
            }
        ) if picture_data else None
    )

    if not product_record:
        raise HTTPException(status_code=500, detail=string_500)

    await autosave_file(product_record.media.storage_href, picture_data)

    dto = ProductGETSchema.model_validate(product_record, from_attributes=True)

    return dto


@router_products.get('/getOwned')
async def get_owned_products(org_id: int,
                             user: UserModel = Depends(authed)):
    try:
        organization, membership = await check_access(org_id, user.id, 2)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    products = await ProductsRepository.get_owned_by_org_id(org_id)

    dto = [ProductGETSchema.model_validate(product, from_attributes=True) for product in products]

    return dto


@router_products.get('/disable')
async def disable_product(product_id: int,
                          user: UserModel = Depends(authed)):
    product = await ProductsRepository.get_one_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    try:
        organization, membership = await check_access(product.org_id, user.id, 2)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    new_product = await ProductsRepository.disable_one(product_id)

    dto = ProductNonRelGETSchema.model_validate(new_product, from_attributes=True)

    return dto


@router_reviews.post('/create')
async def create_review(data: Annotated[ReviewPOSTSchema, Depends()],
                        files: List[UploadFile] = File(...),
                        user: UserModel = Depends(authed)
                        ):
    data_dict = data.model_dump()
    if len(files) > 5:
        raise HTTPException(status_code=400, detail=string_product_too_many_files)

    product = await ProductsRepository.get_one_by_id(data_dict.get('product_id'))

    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail=string_products_product_not_found)

    try:
        organization, membership = await check_access(product.org_id, user.id, 8)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    if data_dict.get('size_id'):
        sizes = [size.id for size in product.sizes]
        if data_dict.get('size_id') not in sizes:
            raise HTTPException(status_code=400, detail=string_403)

    if data_dict.get('match_id'):
        if not data_dict.get('size_id'):
            raise HTTPException(status_code=400, detail=string_product_size_not_selected_but_match)

        match = await ReviewsRepository.get_match_by_id(data_dict.get('match_id'))
        if not match:
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
                'owner_id': user.id
            }
        ))

    review_record = await ReviewsRepository.add_one(data, media_schemas)

    if not review_record:
        raise HTTPException(status_code=500, detail=string_500)

    for file in ordered_files:
        await autosave_file(file.href + f".{file.name.rsplit('.', maxsplit=1)[1]}", file.content)

    review_record = await ReviewsRepository.get_one_by_id(review_record.id)

    dto = ReviewGETSchema.model_validate(review_record, from_attributes=True)

    return dto


@router_reviews.get('/getOwned')
async def create_review(org_id: int,
                        user: UserModel = Depends(authed)
                        ) -> list[ReviewGETSchema]:
    try:
        organization, membership = await check_access(org_id, user.id, 8)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    reviews = await ReviewsRepository.get_owned_by_org_id(org_id)

    dto = [ReviewGETSchema.model_validate(review, from_attributes=True) for review in reviews]

    return dto


@router_reviews.get('/disable')
async def disable_review(review_id: int,
                         user: UserModel = Depends(authed)):

    review = await ReviewsRepository.get_one_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail=string_404)

    try:
        organization, membership = await check_access(review.product.org_id, user.id, 8)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    new_review = await ReviewsRepository.disable_one(review_id)

    dto = ReviewGETSchema.model_validate(new_review, from_attributes=True)

    return dto
