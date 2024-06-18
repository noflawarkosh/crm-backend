import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel
from auth.router import authed
from auth.schemas import UserSessionReadSchema
from orgs.repository import OrganizationRepository
from orgs.utils import check_access
from payments.repository import PaymentsRepository
from payments.schemas import BalanceBillCreateSchema, BalanceBillReadSchema, BalanceSourceSchema, \
    BalanceHistoryReadSchema

from strings import *

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post('/createBill')
async def create_organization(data: Annotated[BalanceBillCreateSchema, Depends()],
                              session: UserSessionReadSchema = Depends(authed)
                              ):
    try:
        await check_access(data.org_id, session.user.id, 0)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    await PaymentsRepository.create_bill(data.model_dump())


@router.get('/getBill')
async def create_organization(bill_id: int,
                              session: UserSessionReadSchema = Depends(authed)
                              ) -> BalanceBillReadSchema:
    bills = await PaymentsRepository.read_bills('id', bill_id)

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    bill = bills[0]

    try:
        await check_access(bill.org_id, session.user.id, 0)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    return BalanceBillReadSchema.model_validate(bill, from_attributes=True)


@router.get('/getOwnedBills')
async def create_organization(org_id: int,
                              session: UserSessionReadSchema = Depends(authed)
                              ) -> list[BalanceBillReadSchema]:
    try:
        await check_access(org_id, session.user.id, 0)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    bills = await PaymentsRepository.read_bills('org_id', org_id)

    return [BalanceBillReadSchema.model_validate(bill, from_attributes=True) for bill in bills]


@router.post('/updateBillStatus')
async def create_organization(bill_id: int, status_id: int,
                              session: UserSessionReadSchema = Depends(authed)
                              ):
    bills = await PaymentsRepository.read_bills('id', bill_id)

    if len(bills) != 1:
        raise HTTPException(status_code=404, detail=string_404)

    bill = bills[0]

    try:
        organization, membership = await check_access(bill.org_id, session.user.id, 0)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    if status_id not in [2, 4]:
        raise HTTPException(status_code=403, detail=string_403)

    if status_id == 2 and bill.status_id not in [3]:
        raise HTTPException(status_code=403, detail=string_403)

    elif status_id == 4 and bill.status_id not in [3]:
        raise HTTPException(status_code=403, detail=string_403)

    await PaymentsRepository.update_bill(bill_id, {'status_id': status_id})


@router.get('/getActiveSources')
async def create_organization(session: UserSessionReadSchema = Depends(authed)
                              ) -> list[BalanceSourceSchema]:
    sources = await PaymentsRepository.read_active_sources()
    return [BalanceSourceSchema.model_validate(source, from_attributes=True) for source in sources]


@router.get('/getHistory')
async def create_organization(org_id: int,
                              session: UserSessionReadSchema = Depends(authed)
                              ) -> list[BalanceHistoryReadSchema]:
    try:
        await check_access(org_id, session.user.id, 0)

    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    history = await PaymentsRepository.read_history(org_id)
    return [BalanceHistoryReadSchema.model_validate(line, from_attributes=True) for line in history]



