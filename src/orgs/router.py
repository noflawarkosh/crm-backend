import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException

from auth.router import authed
from auth.schemas import UserSessionReadSchema
from orgs.schemas import (
    OrganizationCreateSchema,
    OrganizationReadSchema,
    OrganizationInvitationCreateSchema,
    OrganizationInvitationReadSchema, OrganizationMembershipReadSchema
)
from orgs.repository import (
    OrganizationRepository,
    InvitationRepository,
    MembershipRepository
)
from orgs.utils import generate_invitation_code, check_access
from strings import *

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


# Organizations
@router.post('/createOrganization')
async def create_organization(data: Annotated[OrganizationCreateSchema, Depends()],
                              session: UserSessionReadSchema = Depends(authed)):
    await OrganizationRepository.create_organization({**data.model_dump(), 'owner_id': session.user.id})


@router.get('/readOrganizations')
async def read_user_organizations(session: UserSessionReadSchema = Depends(authed)) -> list[OrganizationReadSchema]:
    organizations = await OrganizationRepository.read_organizations('owner_id', session.user.id)
    return [OrganizationReadSchema.model_validate(organization, from_attributes=True) for organization in organizations]


@router.get('/readOrganization')
async def read_user_organization(org_id: int, session: UserSessionReadSchema = Depends(authed)
                                 ) -> OrganizationReadSchema:
    try:
        organization, membership = await check_access(org_id, session.user.id, 0)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    return OrganizationReadSchema.model_validate(organization, from_attributes=True)


# Invitations
@router.post('/createInvitation')
async def create_invitation(data: Annotated[OrganizationInvitationCreateSchema, Depends()],
                            session: UserSessionReadSchema = Depends(authed)):
    try:
        await check_access(data.org_id, session.user.id, 0)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    if data.expires <= datetime.datetime.now():
        raise HTTPException(status_code=400, detail=string_inv_wrong_expires)

    invitations = await InvitationRepository.read_invitations('org_id', data.org_id)

    if len(invitations) >= 5:
        raise HTTPException(status_code=403, detail=string_inv_max_invitations)

    await InvitationRepository.create_invitation({**data.model_dump(), 'code': generate_invitation_code()})


@router.get('/readInvitations')
async def read_invitations(org_id: int,
                           session: UserSessionReadSchema = Depends(authed)
                           ) -> list[OrganizationInvitationReadSchema]:
    try:
        organization, membership = await check_access(org_id, session.user.id, -1)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    invitations = await InvitationRepository.read_invitations('org_id', org_id)

    return [OrganizationInvitationReadSchema.model_validate(row, from_attributes=True) for row in invitations]


@router.get('/disableInvitation')
async def disable_invitations(invitation_id: int,
                              session: UserSessionReadSchema = Depends(authed)):
    invitations = await InvitationRepository.read_invitations('id', invitation_id)

    if len(invitations) != 1:
        raise HTTPException(status_code=404, detail=string_inv_not_found)

    invitation = invitations[0]

    try:
        organization, membership = await check_access(invitation.org_id, session.user.id, 0)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    await InvitationRepository.disable_invitation(invitation.id)


@router.post('/acceptInvitation')
async def accept_invitation(code: str,
                            session: UserSessionReadSchema = Depends(authed)):
    invitations = await InvitationRepository.read_invitations('code', code)

    if len(invitations) != 1:
        raise HTTPException(status_code=404, detail=string_inv_not_found)

    invitation = invitations[0]

    if invitation.expires <= datetime.datetime.now():
        raise HTTPException(status_code=403, detail=string_inv_expired)

    invitation_usages = await MembershipRepository.read_memberships('invitation_id', invitation.id)

    if len(invitation_usages) >= invitation.amount:
        raise HTTPException(status_code=403, detail=string_inv_max_usages)

    organizations = await OrganizationRepository.read_organizations('id', invitation.org_id)

    if len(organizations) != 1:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    organization = organizations[0]

    if organization.owner_id == session.user.id:
        raise HTTPException(status_code=403, detail=string_inv_owner_error)

    current_membership = await MembershipRepository.read_current(session.user.id, organization.id)

    if current_membership:

        if current_membership.status_id == 1:
            raise HTTPException(status_code=403, detail=string_inv_already_member)

        if current_membership.status_id == 4:
            raise HTTPException(status_code=403, detail=string_inv_blocked_member)

    await MembershipRepository.create_membership({
        'org_id': organization.id,
        'user_id': session.user.id,
        'level': invitation.level,
        'status_id': 1,
        'invitation_id': invitation.id
    })


# Membership
@router.get('/readUserMemberships')
async def read_memberships_of_user(session: UserSessionReadSchema = Depends(authed)
                                   ) -> list[OrganizationMembershipReadSchema]:
    return [OrganizationMembershipReadSchema.model_validate(membership, from_attributes=True)
            for membership in await MembershipRepository.read_memberships_of_user(session.user.id)]


@router.get('/readOrganizationMemberships')
async def read_memberships_of_organization(org_id: int, session: UserSessionReadSchema = Depends(authed)):
    try:
        organization, membership = await check_access(org_id, session.user.id, 0)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    users = await MembershipRepository.read_memberships_of_organization(org_id)
    dto = [OrganizationMembershipReadSchema.model_validate(row, from_attributes=True) for row in users]

    return dto


@router.post('/updateMember')
async def update_membership(member_id: int,
                            org_id: int,
                            status_id: int,
                            session: UserSessionReadSchema = Depends(authed)):
    try:
        organization, membership = await check_access(org_id, session.user.id, 0)

    except Exception as exception:
        raise HTTPException(status_code=400, detail=str(exception))

    current_membership = await MembershipRepository.read_current(member_id, org_id)

    if not current_membership:
        raise HTTPException(status_code=400, detail=string_orgs_member_not_found)

    if status_id == current_membership.status_id:
        raise HTTPException(status_code=403, detail=string_orgs_member_status_already_set)

    new_status = None

    if status_id == 4:
        new_status = 4

    elif status_id == 5:
        new_status = 5

    elif status_id == 3:
        if current_membership.status_id != 1:
            raise HTTPException(status_code=403)

    if not new_status:
        raise HTTPException(status_code=403, detail=string_403)

    await MembershipRepository.create_membership({
        'user_id': member_id,
        'org_id': organization.id,
        'level': 0,
        'status_id': new_status,
        'invitation_id': None
    })
