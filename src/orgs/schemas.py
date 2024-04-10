import datetime
from typing import Optional
from pydantic import BaseModel, constr


class OrganizationStatusSchema(BaseModel):
    id: int
    title: str


class OrganizationStatusHistorySchema(BaseModel):
    description: str | None
    date: datetime.datetime
    status: OrganizationStatusSchema


class OrganizationPOSTSchema(BaseModel):
    title: constr(max_length=200)
    inn: constr(min_length=10, max_length=12)


class OrganizationGETSchema(OrganizationPOSTSchema):
    id: int


class OrganizationRELSchema(OrganizationGETSchema):
    statuses: list['OrganizationStatusHistorySchema']


class OrganizationInvitationPOSTSchema(BaseModel):
    level: int
    expires: datetime.datetime
    amount: int


class OrganizationInvitationGETSchema(OrganizationInvitationPOSTSchema):
    id: int
    org_id: int
    code: str
    created: datetime.datetime


class OrganizationInvitationRELSchema(OrganizationInvitationGETSchema):
    organization: OrganizationGETSchema
