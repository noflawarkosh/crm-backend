import datetime
from typing import Optional
from pydantic import BaseModel, constr


# Organization status
from auth.schemas import UserReadFullSchema


class OrganizationStatusSchema(BaseModel):
    id: int
    title: str


class OrganizationStatusHistorySchema(BaseModel):
    description: str | None
    date: datetime.datetime
    status: OrganizationStatusSchema


# Organization
class OrganizationCreateSchema(BaseModel):
    title: constr(max_length=200)
    inn: constr(min_length=10, max_length=12)


class OrganizationReadSchema(OrganizationCreateSchema):
    id: int
    statuses: list['OrganizationStatusHistorySchema']


# Membership
class OrganizationMembershipCreateSchema(BaseModel):
    user_id: int
    org_id: int
    level: int
    status_id: int
    invitation_id: Optional[int | None]


class OrganizationMembershipReadSchema(OrganizationMembershipCreateSchema):
    id: int
    date: datetime.datetime
    user: 'UserReadFullSchema'
    organization: 'OrganizationReadSchema'
    status: OrganizationStatusSchema


# Invitation
class OrganizationInvitationCreateSchema(BaseModel):
    org_id: int
    level: int
    expires: datetime.datetime
    amount: int


class OrganizationInvitationReadSchema(OrganizationInvitationCreateSchema):
    id: int
    org_id: int
    code: str
    created: datetime.datetime
    usages: list['OrganizationMembershipReadSchema'] | None
