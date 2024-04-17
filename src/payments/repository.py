from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import async_session_factory
from payments.models import BalanceBillModel, BalanceSourceModel
from payments.schemas import BalanceBillPOSTSchema


class PaymentsRepository:

    @classmethod
    async def add_bill(cls, data: BalanceBillPOSTSchema) -> BalanceBillModel:

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

    @classmethod
    async def get_bill(cls, bill_id: int) -> BalanceBillModel:

        try:

            async with async_session_factory() as session:

                query = (
                    select(BalanceBillModel)
                    .options(
                        selectinload(BalanceBillModel.organization),
                        selectinload(BalanceBillModel.source),
                        selectinload(BalanceBillModel.status),
                        selectinload(BalanceBillModel.media),
                    )
                    .where(BalanceBillModel.id == bill_id)
                )

                db_response = await session.execute(query)
                bill = db_response.scalars().one_or_none()

                return bill

        finally:
            await session.close()

    @classmethod
    async def get_all_by_org_id(cls, org_id: int) -> list[BalanceBillModel]:

        try:

            async with async_session_factory() as session:

                query = (
                    select(BalanceBillModel)
                    .where(BalanceBillModel.org_id == org_id)
                    .options(
                        selectinload(BalanceBillModel.organization),
                        selectinload(BalanceBillModel.source),
                        selectinload(BalanceBillModel.status),
                        selectinload(BalanceBillModel.media),
                    )
                )

                db_response = await session.execute(query)
                bills = db_response.scalars().all()

                return bills

        finally:
            await session.close()

    @classmethod
    async def update_bill_status(cls, bill_id: int, status_id: int) -> BalanceBillModel | None:

        try:

            async with async_session_factory() as session:

                query = (
                    select(BalanceBillModel)
                    .where(BalanceBillModel.id == bill_id)
                )

                db_response = await session.execute(query)
                bill = db_response.scalars().one_or_none()

                if bill:
                    bill.status_id = status_id

                    await session.commit()
                    await session.refresh(bill)

                    return bill

                return None

        finally:
            await session.close()

    @classmethod
    async def get_active_sources(cls) -> list[BalanceSourceModel]:

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
