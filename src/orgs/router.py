import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException

from auth.models import UserModel
from auth.utils import authed

from orgs.schemas import (
    OrganizationPOSTSchema,
    OrganizationRELSchema,
    OrganizationGETSchema,
    OrganizationInvitationPOSTSchema,
    OrganizationInvitationGETSchema,
    OrganizationInvitationRELSchema,
    OrganizationMembershipGETSchema,
    OrganizationMembershipPOSTSchema,
    OrganizationMembershipRELSchema, OrganizationMembershipRELwOrgSchema, OrganizationInvitationDTOSchema
)

from orgs.repository import (
    OrganizationRepository,
    InvitationRepository,
    MembershipRepository
)
from orgs.utils import generate_invitation_code

from strings import *

router = APIRouter(
    prefix="/orgs",
    tags=["Organizations"]
)


@router.post('/createOrganization')
async def create_organization(data: Annotated[OrganizationPOSTSchema, Depends()],
                              user: UserModel = Depends(authed)
                              ) -> OrganizationGETSchema:
    """
    Registration of organization
    :param data: organization post schema
    :param user: identified user by cookie token (strictly authed)
    :return: organization get schema
    """

    result = await OrganizationRepository.add_one(data, user.id)
    dto = OrganizationGETSchema.model_validate(result, from_attributes=True)

    return dto


@router.get('/getOwned')
async def get_all_organizations_owned_by_user(user: UserModel = Depends(authed)
                                              ) -> list[OrganizationRELSchema]:
    """
    Getting all organizations which owned by the user
    :param user: identified user by cookie token (strictly authed)
    :return: list of organization get schemas
    """

    organizations = await OrganizationRepository.get_orgs_by_owner_id(user.id)
    dto = [OrganizationRELSchema.model_validate(organization, from_attributes=True) for organization in organizations]

    return dto


@router.get('/getOrg')
async def get_certain_organization_by_id(org_id: int, user: UserModel = Depends(authed)
                                         ) -> OrganizationRELSchema:
    """
    Getting certain organization by id if user is owner only
    :param org_id: organization identifier
    :param user: identified user by cookie token (strictly authed)
    :return: organization get schema
    """

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    dto = OrganizationRELSchema.model_validate(organization, from_attributes=True)

    return dto


@router.post('/createInvitation')
async def create_invitation(data: Annotated[OrganizationInvitationPOSTSchema, Depends()],
                            user: UserModel = Depends(authed)
                            ) -> OrganizationInvitationGETSchema:
    """
    Creating invitation
    :param data: invitation schema
    :param user: identified user by cookie token (strictly authed)
    :return: invitation get schema
    """

    data_dict = data.model_dump()
    organization = await OrganizationRepository.get_one(data_dict.get('org_id'))

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    invitation = await InvitationRepository.add_one(
        OrganizationInvitationDTOSchema(**data_dict, code=generate_invitation_code())
    )

    dto = OrganizationInvitationGETSchema.model_validate(invitation, from_attributes=True)

    return dto


@router.get('/getAllInvitations')
async def get_all_invitations_by_org_id(org_id: int,
                                        user: UserModel = Depends(authed)
                                        ) -> list[OrganizationInvitationRELSchema]:
    """
    Getting all invitations of certain organization
    :param org_id:
    :param user: identified user by cookie token (strictly authed)
    :return: list of invitation get schemas
    """

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403, detail=string_403)

    invitations = await InvitationRepository.get_all_by_org_id(org_id)
    dto = [OrganizationInvitationRELSchema.model_validate(row, from_attributes=True) for row in invitations]

    return dto


@router.post('/acceptInvitation')
async def accept_invitation(code: str,
                            user: UserModel = Depends(authed)
                            ) -> OrganizationMembershipGETSchema:
    """
    Accepting invitation by code
    :param code: unique code (XXX-XXX-XXX)
    :param user: identified user by cookie token (strictly authed)
    :return: membership get schema
    """

    invitation = await InvitationRepository.get_one_by_code(code)

    if not invitation:
        raise HTTPException(status_code=404, detail=string_inv_not_found)

    if invitation.expires <= datetime.datetime.now():
        raise HTTPException(status_code=403, detail=string_inv_expired)

    invitation_usages = await MembershipRepository.get_by_invitation_id(invitation.id)

    if len(invitation_usages) >= invitation.amount:
        raise HTTPException(status_code=403, detail=string_inv_max_usages)

    organization = await OrganizationRepository.get_one(invitation.org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id == user.id:
        raise HTTPException(status_code=403, detail=string_inv_owner_error)

    current_membership = await MembershipRepository.get_current(user.id, organization.id)

    if current_membership:

        if current_membership.status_id == 1:
            raise HTTPException(status_code=403, detail=string_inv_alredy_member)

        if current_membership.status_id == 4:
            raise HTTPException(status_code=403, detail=string_inv_blocked_member)

    membership_dict = {
        'org_id': organization.id,
        'user_id': user.id,
        'level': invitation.level,
        'status_id': 1,
        'invitation_id': invitation.id
    }

    data = OrganizationMembershipPOSTSchema.model_validate(membership_dict)

    membership = await MembershipRepository.add_one(data)
    dto = OrganizationMembershipGETSchema.model_validate(membership, from_attributes=True)

    return dto


@router.get('/getOwnedMemberships')
async def get_user_membership_organizations(user: UserModel = Depends(authed)
                                            ) -> list[OrganizationMembershipRELwOrgSchema]:
    """
    Getting organizations in which the user has a membership
    :param user: identified user by cookie token (strictly authed)
    :return: list of organization get schemas
    """

    memberships = await MembershipRepository.get_all_user_memberships(user.id)
    dto = [
        OrganizationMembershipRELwOrgSchema.model_validate(membership, from_attributes=True)
        for membership in memberships
    ]

    return dto


@router.get('/getMembers')
async def get_members_of_organization(org_id: int,
                                      user: UserModel = Depends(authed),
                                      ):
    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403)

    users = await MembershipRepository.get_members_of_org(org_id)
    dto = [OrganizationMembershipRELSchema.model_validate(row, from_attributes=True) for row in users]

    return dto


@router.post('/blockMember')
async def block_member_in_organization(user_id: int,
                                       org_id: int,
                                       user: UserModel = Depends(authed)
                                       ):
    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403)

    current_membership = await MembershipRepository.get_current(user_id, org_id)

    if not current_membership:
        raise HTTPException(status_code=403)

    if current_membership.status_id == 4:
        raise HTTPException(status_code=403)

    data_dict = {
        'user_id': user_id,
        'org_id': org_id,
        'level': 0,
        'status_id': 4,
        'invitation_id': None
    }

    data = OrganizationMembershipPOSTSchema.model_validate(data_dict)

    new_membership = await MembershipRepository.add_one(data)

    dto = OrganizationMembershipGETSchema.model_validate(new_membership, from_attributes=True)

    return dto


@router.post('/unblockMember')
async def block_member_in_organization(user_id: int,
                                       org_id: int,
                                       user: UserModel = Depends(authed)
                                       ):
    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403)

    current_membership = await MembershipRepository.get_current(user_id, org_id)

    if not current_membership:
        raise HTTPException(status_code=403)

    if current_membership.status_id == 5:
        raise HTTPException(status_code=403)

    data_dict = {
        'user_id': user_id,
        'org_id': org_id,
        'level': 0,
        'status_id': 5,
        'invitation_id': None
    }

    data = OrganizationMembershipPOSTSchema.model_validate(data_dict)

    new_membership = await MembershipRepository.add_one(data)

    dto = OrganizationMembershipGETSchema.model_validate(new_membership, from_attributes=True)

    return dto


@router.post('/kickMember')
async def block_member_in_organization(user_id: int,
                                       org_id: int,
                                       user: UserModel = Depends(authed)
                                       ):
    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        raise HTTPException(status_code=404, detail=string_orgs_org_not_found)

    if organization.owner_id != user.id:
        raise HTTPException(status_code=403)

    current_membership = await MembershipRepository.get_current(user_id, org_id)

    if not current_membership:
        raise HTTPException(status_code=403)

    if current_membership.status_id != 1:
        raise HTTPException(status_code=403)

    data_dict = {
        'user_id': user_id,
        'org_id': org_id,
        'level': 0,
        'status_id': 3,
        'invitation_id': None
    }

    data = OrganizationMembershipPOSTSchema.model_validate(data_dict)

    new_membership = await MembershipRepository.add_one(data)

    dto = OrganizationMembershipGETSchema.model_validate(new_membership, from_attributes=True)

    return dto
