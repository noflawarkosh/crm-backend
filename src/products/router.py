from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel
from auth.utils import authed
from orgs.repository import OrganizationRepository
from products.schemas import ProductPOSTSchema
from strings import *

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.post('/create')
async def create_organization(data: Annotated[ProductPOSTSchema, Depends()],
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


