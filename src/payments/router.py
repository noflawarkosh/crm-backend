from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel
from auth.router import authed
from orgs.repository import OrganizationRepository
from payments.repository import PaymentsRepository
from payments.schemas import BalanceBillPOSTSchema, BalanceBillGETSchema, BalanceBillRELSchema, BalanceSourceGETSchema
from strings import *

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post('/createBill')
async def create_organization(data: Annotated[BalanceBillPOSTSchema, Depends()],
                              user: UserModel = Depends(authed)
                              ) -> BalanceBillGETSchema:
    data_dict = data.model_dump()

    organization = await OrganizationRepository.get_one(data_dict.get('org_id'))

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    result = await PaymentsRepository.add_bill(data)
    dto = BalanceBillGETSchema.model_validate(result, from_attributes=True)

    return dto


@router.get('/getBill')
async def create_organization(bill_id: int,
                              user: UserModel = Depends(authed)
                              ) -> BalanceBillRELSchema:
    bill = await PaymentsRepository.get_bill(bill_id)

    if not bill:
        raise HTTPException(status_code=404, detail=string_404)

    organization = await OrganizationRepository.get_one(bill.org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    dto = BalanceBillRELSchema.model_validate(bill, from_attributes=True)

    return dto


@router.post('/cancelBill')
async def create_organization(bill_id: int,
                              user: UserModel = Depends(authed)
                              ) -> BalanceBillGETSchema:
    bill = await PaymentsRepository.get_bill(bill_id)

    if not bill:
        raise HTTPException(status_code=404, detail=string_404)

    organization = await OrganizationRepository.get_one(bill.org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    if bill.status_id != 3:
        raise HTTPException(status_code=403, detail=string_403)

    updated_bill = await PaymentsRepository.update_bill_status(bill_id, 4)

    dto = BalanceBillGETSchema.model_validate(updated_bill, from_attributes=True)

    return dto


@router.post('/approveSendingMoneyBill')
async def create_organization(bill_id: int,
                              user: UserModel = Depends(authed)
                              ) -> BalanceBillGETSchema:
    bill = await PaymentsRepository.get_bill(bill_id)

    if not bill:
        raise HTTPException(status_code=404, detail=string_404)

    organization = await OrganizationRepository.get_one(bill.org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    if bill.status_id != 3:
        raise HTTPException(status_code=403, detail=string_403)

    updated_bill = await PaymentsRepository.update_bill_status(bill_id, 2)

    dto = BalanceBillGETSchema.model_validate(updated_bill, from_attributes=True)

    return dto


@router.get('/getOwnedBills')
async def create_organization(org_id: int,
                              user: UserModel = Depends(authed)
                              ) -> list[BalanceBillRELSchema]:
    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    bills = await PaymentsRepository.get_all_by_org_id(org_id)
    dto = [BalanceBillRELSchema.model_validate(bill, from_attributes=True) for bill in bills]

    return dto


@router.get('/getActiveSources')
async def create_organization(user: UserModel = Depends(authed)
                              ) -> list[BalanceSourceGETSchema]:
    sources = await PaymentsRepository.get_active_sources()
    dto = [BalanceSourceGETSchema.model_validate(source, from_attributes=True) for source in sources]

    return dto
