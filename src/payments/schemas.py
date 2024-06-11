import datetime
from typing import Optional
from pydantic import BaseModel, constr

from orgs.schemas import OrganizationReadSchema
from storage.schemas import StorageGETSchema


class BalanceActionSchema(BaseModel):
    id: int
    title: str


class BalanceHistoryGETSchema(BaseModel):
    id: int
    action_id: int
    description: str | None
    org_id: int
    amount: int
    date: datetime.datetime


class BalanceHistoryRELSchema(BalanceHistoryGETSchema):
    organization: 'OrganizationReadSchema'
    action: BalanceActionSchema


class BalanceSourcePOSTSchema(BaseModel):
    title: str
    description: str | None
    number: str
    is_active: bool


class BalanceSourceGETSchema(BalanceSourcePOSTSchema):
    id: int


class BalanceBillStatusSchema(BaseModel):
    id: int
    title: str


class BalanceBillPOSTSchema(BaseModel):
    org_id: int
    amount: int
    source_id: int


class BalanceBillGETSchema(BalanceBillPOSTSchema):
    id: int
    status_id: int
    media_id: int | None
    date: datetime.datetime


class BalanceBillRELSchema(BalanceBillGETSchema):

    organization: 'OrganizationReadSchema'
    source: BalanceSourceGETSchema
    status: BalanceBillStatusSchema
    media: 'StorageGETSchema'
