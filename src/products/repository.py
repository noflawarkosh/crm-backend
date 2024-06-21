from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from database import async_session_factory
from products.models import ProductModel, ReviewModel, ReviewMediaModel, ProductSizeModel
from products.schemas import ProductCreateSchema, ProductSizeCreateSchema, ReviewCreateSchema

from storage.models import StorageModel
from storage.repository import StorageRepository
from storage.schemas import StoragePOSTSchema


class ProductsRepository:

    @classmethod
    async def create_product(cls, product_schema: ProductCreateSchema, size_schemas: list[ProductSizeCreateSchema],
                             media_schema: StoragePOSTSchema = None) -> ProductModel:

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

                return product

        finally:
            await session.close()


class ReviewsRepository:

    @classmethod
    async def create_review(cls, review_schema: ReviewCreateSchema, media_schemas: list[StoragePOSTSchema]
                            ) -> ReviewModel:

        try:
            async with async_session_factory() as session:

                # Add review
                review = ReviewModel(**review_schema.model_dump(), status=1)
                session.add(review)
                await session.flush()

                # Add media
                storage_records = []
                for media_schema in media_schemas:
                    storage_records.append(StorageModel(**media_schema.model_dump()))
                session.add_all(storage_records)
                await session.flush()

                # Add review media
                for storage_record in storage_records:
                    session.add(ReviewMediaModel(review_id=review.id, media_id=storage_record.id))

                await session.commit()
                await session.refresh(review)
                return review

        finally:
            await session.close()

    @classmethod
    async def get_owned_by_org_id(cls, org_id: int) -> list[ReviewModel] | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(ReviewModel, ProductModel)
                    .options(
                        selectinload(ReviewModel.media),
                        selectinload(ReviewModel.product),
                        selectinload(ReviewModel.size),
                        selectinload(ProductModel.media)
                    )
                    .filter(ProductModel.org_id == org_id)
                    .filter(ProductModel.is_active)
                )

                db_response = await session.execute(query)
                reviews = db_response.scalars().all()

                return reviews

        finally:
            await session.close()
