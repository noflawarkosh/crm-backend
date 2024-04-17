from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import async_session_factory
from products.models import ProductModel
from products.schemas import ProductPOSTSchema


class ProductsRepository:

    @classmethod
    async def add_product(cls, data: ProductPOSTSchema) -> ProductModel:

        try:

            async with async_session_factory() as session:

                data_dict = data.model_dump()
                data_dict['status_id'] = 3

                bill = BalanceBillModel(**data_dict)
                session.add(bill)

                await session.commit()
                await session.refresh(bill)

                return bill

        finally:
            await session.close()

