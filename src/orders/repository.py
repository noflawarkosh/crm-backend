import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database import async_session_factory
from orders.models import OrdersOrderModel


class OrdersRepository:
    @classmethod
    async def read_plan(cls, org_id: int, date: datetime.datetime) -> list[OrdersOrderModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(OrdersOrderModel)
                    .where(
                        and_(
                            OrdersOrderModel.org_id == org_id,
                            OrdersOrderModel.dt_planed == date
                        )
                    )
                    .options(
                        selectinload(OrdersOrderModel.product),
                        selectinload(OrdersOrderModel.size),
                    )
                )

                db_response = await session.execute(query)
                plan = db_response.unique().scalars().all()

                return plan
        finally:
            await session.close()

    @classmethod
    async def save_plan(cls, data: dict, amount: int):
        try:
            async with async_session_factory() as session:
                orders = []
                for i in range(0, amount):
                    orders.append(OrdersOrderModel(**data))


                for order in orders:
                    session.add(order)

                await session.commit()
        finally:
            await session.close()
