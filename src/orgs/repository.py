from fastapi import HTTPException
from sqlalchemy import select, and_, func, tuple_
from sqlalchemy.orm import selectinload, aliased

from database import async_session_factory
from orgs.utils import generate_invitation_code
from strings import *

from orgs.models import (
    OrganizationStatusHistoryModel,
    OrganizationModel,
    OrganizationInvitationModel,
    OrganizationMembershipModel
)

from orgs.schemas import (
    OrganizationGETSchema,
    OrganizationPOSTSchema,
    OrganizationRELSchema,
    OrganizationInvitationGETSchema,
    OrganizationInvitationPOSTSchema,
    OrganizationMembershipPOSTSchema
)


class OrganizationRepository:

    @classmethod
    async def add_one(cls, data: OrganizationPOSTSchema, user_id: int) -> OrganizationModel:

        """
        Organization insertion
        :param data: schema of organization for insertion
        :param user_id: identifier of user which will be set as owner_id
        :return: inserted organization ORM
        """

        try:

            async with async_session_factory() as session:

                # Check INN is unique
                query = (
                    select(OrganizationModel.inn)
                    .where(OrganizationModel.inn == data.inn)
                )

                db_response = await session.execute(query)

                if db_response.all():
                    raise HTTPException(status_code=409, detail=string_orgs_inn_not_unique)

                # Dumping pydantic model to dict
                data_dict = data.model_dump()

                # Init, add and flush new organization
                new_org = OrganizationModel(**data_dict)
                new_org.owner_id = user_id
                session.add(new_org)
                await session.flush()

                # Setting active status to new_org
                new_org_status = OrganizationStatusHistoryModel(org_id=new_org.id, status_id=1)
                session.add(new_org_status)

                await session.commit()
                await session.refresh(new_org)

                return new_org

        finally:
            await session.close()

    @classmethod
    async def get_orgs_by_owner_id(cls, owner_id: int) -> list[OrganizationModel]:

        """
        Get list of organizations owned by user
        :param owner_id: identifier of user as owner_id
        :return: list of organization ORMs with joined statuses
        """

        try:
            async with async_session_factory() as session:

                query = (
                    select(OrganizationModel)
                    .options(selectinload(OrganizationModel.statuses))
                    .where(OrganizationModel.owner_id == owner_id)
                )

                db_response = await session.execute(query)
                return db_response.scalars().all()

        finally:
            await session.close()

    @classmethod
    async def get_one(cls, org_id: int) -> OrganizationModel:

        """
        Get one organization by id or None
        :param org_id: identifier of organization
        :return: organization ORM or None
        """

        try:
            async with async_session_factory() as session:

                query = (
                    select(OrganizationModel)
                    .options(selectinload(OrganizationModel.statuses))
                    .where(OrganizationModel.id == org_id)
                )

                db_response = await session.execute(query)
                organization = db_response.scalars().one_or_none()

                return organization

        finally:
            await session.close()


class InvitationRepository:

    @classmethod
    async def add_one(cls, data: OrganizationInvitationPOSTSchema) -> OrganizationInvitationModel:

        """
        Invitation insertions
        :param data: schema of invitation for insertion
        :return: inserted invitation ORM
        """

        try:

            async with async_session_factory() as session:

                data_dict = data.model_dump()
                data_dict['code'] = generate_invitation_code()
                new_invitation = OrganizationInvitationModel(**data_dict)
                session.add(new_invitation)

                await session.commit()
                await session.refresh(new_invitation)

                return new_invitation

        finally:
            await session.close()

    @classmethod
    async def get_all_by_org_id(cls, org_id: int) -> list[OrganizationInvitationModel]:

        """
        Get all invitations of organizations
        :param org_id: organization identifier
        :return: list of invitation ORMs with joined [users which used invitations, datetime when used]
        """

        try:

            async with async_session_factory() as session:

                query = (
                    select(OrganizationInvitationModel)
                    .where(
                        and_(
                            OrganizationInvitationModel.org_id == org_id,
                            OrganizationInvitationModel.expires > func.now()
                        )
                    )
                    .options(
                        selectinload(OrganizationInvitationModel.usages)
                    )
                )

                db_response = await session.execute(query)
                invitations = db_response.scalars().all()

                return invitations

        finally:
            await session.close()

    @classmethod
    async def get_one_by_code(cls, code: str) -> OrganizationInvitationModel:

        """
        Get invitation with certain code
        :param code: invitation code (XXX-XXX-XXX)
        :return: invitation ORM or None
        """

        try:

            async with async_session_factory() as session:

                query = (
                    select(OrganizationInvitationModel)
                    .where(OrganizationInvitationModel.code == code)
                )

                db_response = await session.execute(query)
                invitation = db_response.scalars().one_or_none()

                return invitation

        finally:
            await session.close()


class MembershipRepository:

    @classmethod
    async def add_one(cls, data: OrganizationMembershipPOSTSchema) -> OrganizationMembershipModel:

        try:

            async with async_session_factory() as session:

                data_dict = data.model_dump()

                membership = OrganizationMembershipModel(**data_dict)
                session.add(membership)

                await session.commit()
                await session.refresh(membership)

                return membership

        finally:
            await session.close()

    @classmethod
    async def get_by_invitation_id(cls, inv_id: int) -> list[OrganizationMembershipModel]:

        """
        Get all membership record with certain invitation identifier (invitation usages)
        :param inv_id: invitation identifier
        :return: list of membership ORMs
        """

        try:

            async with async_session_factory() as session:

                query = (
                    select(OrganizationMembershipModel)
                    .where(
                        OrganizationMembershipModel.invitation_id == inv_id
                    )
                )

                db_response = await session.execute(query)
                invitation_usages = db_response.scalars().all()

                return invitation_usages

        finally:
            await session.close()

    @classmethod
    async def get_current(cls, user_id: int, org_id: int) -> OrganizationMembershipModel:

        """
        Get current membership state of certain user in certain organization
        :param user_id: identifier of user
        :param org_id: identifier of organization
        :return: membership ORM or None
        """

        try:

            async with async_session_factory() as session:

                query = (
                    select(OrganizationMembershipModel)
                    .where(
                        and_(
                            OrganizationMembershipModel.user_id == user_id,
                            OrganizationMembershipModel.org_id == org_id
                        )
                    )
                    .order_by(OrganizationMembershipModel.date.desc())
                    .limit(1)
                )

                db_response = await session.execute(query)
                current = db_response.scalars().one_or_none()

                return current

        finally:
            await session.close()

    @classmethod
    async def get_all_user_statuses_in_orgs(cls, user_id: int) -> list:

        """
        Getting all user's current memberships (statuses in organizations)
        :param user_id:
        :return: list of tuples (org_id, status_id)
        """

        try:

            async with async_session_factory() as session:

                subquery = (
                    select(
                        OrganizationMembershipModel.org_id,
                        func.max(OrganizationMembershipModel.date).label('max_date')
                    )
                    .where(OrganizationMembershipModel.user_id == user_id)
                    .group_by(OrganizationMembershipModel.org_id)
                    .alias()
                )

                query = (
                    select(OrganizationMembershipModel.org_id, OrganizationMembershipModel.status_id)
                    .select_from(OrganizationMembershipModel)
                    .join(subquery, and_(
                        OrganizationMembershipModel.org_id == subquery.c.org_id,
                        OrganizationMembershipModel.date == subquery.c.max_date
                    ))
                    .where(OrganizationMembershipModel.user_id == user_id)
                )

                db_response = await session.execute(query)
                list_of_statuses_in_orgs = db_response.all()

                return list_of_statuses_in_orgs

        finally:
            await session.close()

    @classmethod
    async def get_all_user_memberships(cls, user_id: int) -> list[OrganizationMembershipModel]:

        try:

            async with async_session_factory() as session:

                subquery = select(
                    OrganizationMembershipModel.user_id,
                    OrganizationMembershipModel.org_id,
                    func.max(OrganizationMembershipModel.date)
                ).where(
                    OrganizationMembershipModel.user_id == user_id
                ).group_by(
                    OrganizationMembershipModel.user_id,
                    OrganizationMembershipModel.org_id
                ).alias()

                query = select(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.user_id == user_id
                ).where(
                    tuple_(
                        OrganizationMembershipModel.user_id,
                        OrganizationMembershipModel.org_id,
                        OrganizationMembershipModel.date
                    ).in_(subquery)
                ).options(selectinload(OrganizationMembershipModel.organization))

                db_response = await session.execute(query)
                memberships = db_response.scalars().all()

                return memberships

        finally:
            await session.close()

    @classmethod
    async def get_members_of_org(cls, org_id: int) -> list[OrganizationMembershipModel]:

        try:
            async with async_session_factory() as session:

                subquery = (
                    select(
                        func.max(OrganizationMembershipModel.date).label("max_date")
                    )
                    .where(OrganizationMembershipModel.org_id == org_id)
                    .group_by(OrganizationMembershipModel.user_id)
                    .subquery()
                )

                query = (
                    select(OrganizationMembershipModel)
                    .where(
                        and_(
                            OrganizationMembershipModel.org_id == org_id,
                            OrganizationMembershipModel.date == subquery.c.max_date
                        )
                    )
                    .options(
                        selectinload(OrganizationMembershipModel.user),
                        selectinload(OrganizationMembershipModel.status),

                    )
                    .order_by(OrganizationMembershipModel.status_id.asc())
                )

                db_response = await session.execute(query)
                result = db_response.scalars().all()

                return result
        finally:
            await session.close()
