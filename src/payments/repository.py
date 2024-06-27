from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database import async_session_factory
from orders.models import OrdersOrderModel
from payments.models import BalanceBillModel, BalanceSourceModel, BalanceHistoryModel


class PaymentsRepository:
    @classmethod
    async def create_bill(cls, data: dict):
        try:
            async with async_session_factory() as session:

                bill = BalanceBillModel(**data)
                session.add(bill)
                await session.commit()
                await session.refresh(bill)

                return bill.id

        finally:
            await session.close()

    @classmethod
    async def pay_tasks(cls, orders: list, total: int, org_id: int, rate_name: str):
        try:
            async with async_session_factory() as session:

                session.add(BalanceHistoryModel(
                    description=f'Оплата задач ({len(orders)}) по тарифу ({rate_name}): {[o["id"] for o in orders]}',
                    amount=total,
                    org_id=org_id,
                    action_id=2
                ))

                for order in orders:
                    await session.merge(OrdersOrderModel(**order))

                await session.commit()

        finally:
            await session.close()

