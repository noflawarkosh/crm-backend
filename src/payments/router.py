from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from database import DefaultRepository
from payments.repository import PaymentsRepository
from strings import *
from auth.router import authed
from orgs.router import check_access
from auth.models import UserSessionModel
from payments.models import (
    BalanceBillModel,
    BalanceSourceModel,
    BalanceHistoryModel
)
from payments.schemas import (
    BalanceBillCreateSchema,
    BalanceBillReadSchema,
    BalanceSourceSchema,
    BalanceHistoryReadSchema
)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post('/createBill')
async def create_organization(data: Annotated[BalanceBillCreateSchema, Depends()],
                              session: UserSessionModel = Depends(authed)):
    await check_access(data.org_id, session.user.id, 0)

    status_id = 3
    if data.source_id == 1:
        status_id = 6

    bill_id = await PaymentsRepository.create_bill({**data.model_dump(), 'status_id': status_id})
    return bill_id


@router.get('/getBill')
async def create_organization(bill_id: int,
                              session: UserSessionModel = Depends(authed)
                              ) -> BalanceBillReadSchema:
    bills = await DefaultRepository.get_records(
        BalanceBillModel,
        filters=[BalanceBillModel.id == bill_id],
        prefetch_related=[
            BalanceBillModel.source,
            BalanceBillModel.status,
            BalanceBillModel.organization
        ]
    )

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404) if len(bills) == 0 else None

    await check_access(bills[0].org_id, session.user.id, 0)

    return BalanceBillReadSchema.model_validate(bills[0], from_attributes=True)


@router.get('/getOwnedBills')
async def create_organization(org_id: int,
                              session: UserSessionModel = Depends(authed)
                              ) -> list[BalanceBillReadSchema]:
    await check_access(org_id, session.user.id, 0)
    bills = await DefaultRepository.get_records(
        BalanceBillModel,
        filters=[BalanceBillModel.org_id == org_id],
        prefetch_related=[
            BalanceBillModel.source,
            BalanceBillModel.status,
        ]
    )
    return [BalanceBillReadSchema.model_validate(record, from_attributes=True) for record in bills]


@router.post('/updateBillStatus')
async def create_organization(bill_id: int, status_id: int,
                              session: UserSessionModel = Depends(authed)):
    bills = await DefaultRepository.get_records(
        BalanceBillModel,
        filters=[BalanceBillModel.id == bill_id]
    )

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    await check_access(bills[0].org_id, session.user.id, 0)

    if status_id not in [2, 4]:
        raise HTTPException(status_code=403, detail=string_403)

    if status_id == 2 and bills[0].status_id not in [3]:
        raise HTTPException(status_code=403, detail=string_403)

    elif status_id == 4 and bills[0].status_id not in [3]:
        raise HTTPException(status_code=403, detail=string_403)

    await DefaultRepository.save_records(
        [{'model': BalanceBillModel, 'records': [{'id': bill_id, 'status_id': status_id}]}]
    )


@router.get('/getActiveSources')
async def create_organization(session: UserSessionModel = Depends(authed)) -> list[BalanceSourceSchema]:
    sources = await DefaultRepository.get_records(
        BalanceSourceModel,
        filters=[BalanceSourceModel.is_active]
    )
    return [BalanceSourceSchema.model_validate(record, from_attributes=True) for record in sources]


@router.get('/getHistory')
async def create_organization(org_id: int,
                              session: UserSessionModel = Depends(authed)
                              ) -> list[BalanceHistoryReadSchema]:
    await check_access(org_id, session.user.id, 0)
    history = await DefaultRepository.get_records(
        BalanceHistoryModel,
        filters=[BalanceHistoryModel.org_id == org_id],
        select_related=[BalanceHistoryModel.organization, BalanceHistoryModel.action]
    )
    return [BalanceHistoryReadSchema.model_validate(record, from_attributes=True) for record in history]
