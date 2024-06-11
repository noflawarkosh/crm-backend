import random
import string
from strings import *

from orgs.repository import OrganizationRepository, MembershipRepository


def generate_invitation_code():
    random_string = ''
    for i in range(11):
        if i == 3 or i == 7:
            random_string += '-'
        else:
            random_string += random.choice(string.ascii_letters + string.digits)

    return random_string.upper()


async def check_access(org_id: int, user_id: int, level: int):
    organizations = await OrganizationRepository.read_organizations('id', org_id)

    if len(organizations) != 1:
        raise Exception(string_orgs_org_not_found)

    organization = organizations[0]

    if organization.statuses[-1].status_id != 2:
        raise Exception(string_orgs_org_not_active)

    if organization.owner_id == user_id:
        return organization, None

    membership = await MembershipRepository.read_current(user_id, organization.id)

    if not membership or membership.status_id != 1 or not (membership.level & level):
        raise Exception(string_403)

    return organization, membership
