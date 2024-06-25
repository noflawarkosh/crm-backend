import datetime
from typing import Optional
from pydantic import BaseModel, constr

from orgs.schemas import OrganizationReadSchema



# Balance Action
class BalanceActionSchema(BaseModel):
    id: int
    title: str


class BalanceHistoryReadSchema(BaseModel):
    id: int
    action_id: int
    description: str | None
    org_id: int
    amount: int
    date: datetime.datetime

    organization: 'OrganizationReadSchema'
    action: 'BalanceActionSchema'


# Balance Source
class BalanceSourceSchema(BaseModel):
    id: int
    bank: str
    recipient: str
    number: str
    bill: str
    description: str | None
    is_active: bool


# Balance Status
class BalanceBillStatusSchema(BaseModel):
    id: int
    title: str


class BalanceBillCreateSchema(BaseModel):
    org_id: int
    amount: int
    source_id: int


class BalanceBillReadSchema(BalanceBillCreateSchema):
    id: int
    status_id: int
    date: datetime.datetime
    media: Optional[str] = None

    organization: Optional['OrganizationReadSchema']
    source: Optional['BalanceSourceSchema']
    status: Optional['BalanceBillStatusSchema']


