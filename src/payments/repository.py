from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database import async_session_factory
from payments.models import BalanceBillModel, BalanceSourceModel, BalanceHistoryModel


class PaymentsRepository:

    @classmethod
    async def create_bill(cls, data: dict):

        try:
            async with async_session_factory() as session:

                bill = BalanceBillModel(**data, status_id=3)

                session.add(bill)
                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def read_bills(cls, field: str, value) -> list[BalanceBillModel] | None:
        try:
            async with async_session_factory() as session:
                query = (
                    select(BalanceBillModel)
                    .where(getattr(BalanceBillModel, field) == value)
                )

                db_response = await session.execute(query)
                bills = db_response.unique().scalars().all()

                return bills

        finally:
            await session.close()

    @classmethod
    async def update_bill(cls, bill_id: int, values: dict):

        try:
            async with async_session_factory() as session:
                query = (
                    update(BalanceBillModel)
                    .where(BalanceBillModel.id == bill_id)
                    .values(**values)
                )
                await session.execute(query)
                await session.commit()
        finally:
            await session.close()

    @classmethod
    async def read_active_sources(cls) -> list[BalanceSourceModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(BalanceSourceModel)
                    .where(BalanceSourceModel.is_active)
                )

                db_response = await session.execute(query)
                sources = db_response.scalars().all()

                return sources

        finally:
            await session.close()

    @classmethod
    async def read_history(cls, org_id: int) -> list[BalanceHistoryModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(BalanceHistoryModel)
                    .where(BalanceHistoryModel.org_id == org_id)
                )

                db_response = await session.execute(query)
                history = db_response.unique().scalars().all()

                return history
        finally:
            await session.close()


