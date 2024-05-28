from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database import async_session_factory
from products.models import ProductModel, ReviewModel, ReviewMediaModel, ReviewStatusHistoryModel, ProductSizeModel, \
    ReviewMatchModel
from products.schemas import ProductPOSTSchema, ReviewPOSTSchema, \
    ProductSizeInsertSchema, ProductInsertSchema
from storage.models import StorageModel
from storage.repository import StorageRepository
from storage.schemas import StoragePOSTSchema


class ProductsRepository:

    @classmethod
    async def add_one(cls,
                      product_schema: ProductInsertSchema,
                      size_schemas: list[ProductSizeInsertSchema],
                      media_schema: StoragePOSTSchema = None
                      ) -> ProductModel:

        try:

            async with async_session_factory() as session:

                # Add picture
                media_id = None
                if media_schema:
                    media_record = StorageModel(**media_schema.model_dump())

                    session.add(media_record)
                    await session.flush()

                    media_id = media_record.id

                # Add product
                product_schema = product_schema.model_dump()
                product_schema['media_id'] = media_id

                product = ProductModel(**product_schema)

                session.add(product)
                await session.flush()

                # Add sizes
                size_models = []
                for size_schema in size_schemas:
                    size_schema = size_schema.model_dump()
                    size_schema['product_id'] = product.id

                    size_models.append(ProductSizeModel(**size_schema))

                for size in size_models:
                    session.add(size)

                await session.commit()
                await session.refresh(product)

                query = (
                    select(ProductModel)
                    .options(
                        selectinload(ProductModel.sizes),
                        selectinload(ProductModel.media)
                    )
                    .where(ProductModel.id == product.id)
                )

                db_response = await session.execute(query)

                product = db_response.scalars().one_or_none()

                return product

        finally:
            await session.close()

    @classmethod
    async def get_owned_by_org_id(cls, org_id: int) -> list[ProductModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(ProductModel)
                    .options(
                        selectinload(ProductModel.media),
                        selectinload(ProductModel.sizes)
                    )
                    .where(
                        and_(
                            ProductModel.org_id == org_id,
                            ProductModel.is_active
                        )
                    )
                    .order_by(
                        ProductModel.date.desc()
                    )
                )

                db_response = await session.execute(query)
                products = db_response.scalars().all()

                return products

        finally:
            await session.close()

    @classmethod
    async def disable_one(cls, product_id: int) -> ProductModel | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(ProductModel)
                    .where(ProductModel.id == product_id)
                    .options(
                        selectinload(ProductModel.media),
                        selectinload(ProductModel.sizes)
                    )
                )

                db_response = await session.execute(query)

                product = db_response.scalars().one_or_none()

                if not product:
                    return None

                product.is_active = False

                await session.commit()
                await session.refresh(product)

                return product

        finally:
            await session.close()

    @classmethod
    async def get_one_by_id(cls, product_id: int) -> ProductModel | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(ProductModel)
                    .where(ProductModel.id == product_id)
                    .options(
                        selectinload(ProductModel.media),
                        selectinload(ProductModel.sizes)
                    )
                )

                db_response = await session.execute(query)

                product = db_response.scalars().one_or_none()

                return product

        finally:
            await session.close()


class ReviewsRepository:

    @classmethod
    async def get_match_by_id(cls, match_id: int) -> ReviewMatchModel:
        try:
            async with async_session_factory() as session:

                query = (
                    select(ReviewMatchModel)
                    .where(ReviewMatchModel.id == match_id)
                )

                db_response = await session.execute(query)

                match = db_response.scalars().one_or_none()

                return match

        finally:
            await session.close()

    @classmethod
    async def add_one(cls,
                      review_schema: ReviewPOSTSchema,
                      media_schemas: list[StoragePOSTSchema]
                      ) -> ReviewModel:

        try:

            async with async_session_factory() as session:

                review = ReviewModel(**review_schema.model_dump())

                session.add(review)
                await session.flush()

                session.add(ReviewStatusHistoryModel(review_id=review.id, status_id=1))

                storage_records = []
                for media_schema in media_schemas:
                    storage_records.append(StorageModel(**media_schema.model_dump()))

                session.add_all(storage_records)

                await session.flush()

                for storage_record in storage_records:
                    session.add(ReviewMediaModel(review_id=review.id, media_id=storage_record.id))

                await session.commit()
                await session.refresh(review)

                return review
        finally:
            await session.close()

    @classmethod
    async def get_one_by_id(cls, review_id: int) -> ReviewModel | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(ReviewModel)
                    .where(ReviewModel.id == review_id)
                    .options(
                        selectinload(ReviewModel.media),
                        selectinload(ReviewModel.statuses),
                        selectinload(ReviewModel.product),
                        selectinload(ReviewModel.size),
                        selectinload(ReviewModel.match)
                    )
                )

                db_response = await session.execute(query)
                review = db_response.scalars().one_or_none()

                return review

        finally:
            await session.close()

    @classmethod
    async def get_owned_by_org_id(cls, org_id: int) -> list[ReviewModel] | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(ReviewModel)
                    .join(ProductModel)
                    .options(
                        selectinload(ReviewModel.media),
                        selectinload(ReviewModel.statuses),
                        selectinload(ReviewModel.product),
                        selectinload(ReviewModel.size),
                        selectinload(ReviewModel.match),
                    )
                    .filter(ProductModel.org_id == org_id)
                    .filter(ProductModel.is_active)
                )

                db_response = await session.execute(query)
                reviews = db_response.scalars().all()

                return reviews

        finally:
            await session.close()

    @classmethod
    async def disable_one(cls, review_id: int) -> ReviewModel | None:
        try:

            async with async_session_factory() as session:

                session.add(ReviewStatusHistoryModel(review_id=review_id, status_id=4))
                await session.commit()

        finally:

            await session.close()

        return await ReviewsRepository.get_one_by_id(review_id)
