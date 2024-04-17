import datetime
from typing import Optional
from pydantic import BaseModel, constr

from auth.schemas import UserGETSchema, UserPublicSchema


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


class OrganizationGETMembershipSchema(BaseModel):
    user: UserGETSchema
    date: datetime.datetime


class OrganizationInvitationPOSTSchema(BaseModel):
    org_id: int
    level: int
    expires: datetime.datetime
    amount: int


class OrganizationInvitationGETSchema(OrganizationInvitationPOSTSchema):
    id: int
    org_id: int
    code: str
    created: datetime.datetime


class OrganizationInvitationRELSchema(OrganizationInvitationGETSchema):
    usages: list['OrganizationGETMembershipSchema'] | None


class OrganizationMembershipPOSTSchema(BaseModel):
    user_id: int
    org_id: int
    level: int
    status_id: int
    invitation_id: Optional[int | None]


class OrganizationMembershipGETSchema(OrganizationMembershipPOSTSchema):
    id: int
    date: datetime.datetime


class OrganizationMembershipRELSchema(BaseModel):
    user: UserPublicSchema
    level: int
    status: OrganizationStatusSchema
    date: datetime.datetime


class OrganizationMembershipRELwOrgSchema(OrganizationMembershipGETSchema):
    organization: OrganizationGETSchema
