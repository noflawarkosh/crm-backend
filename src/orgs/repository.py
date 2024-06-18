from sqlalchemy import select, and_, func, tuple_, update
from sqlalchemy.orm import selectinload

from database import async_session_factory

from orgs.models import (
    OrganizationStatusHistoryModel,
    OrganizationModel,
    OrganizationInvitationModel,
    OrganizationMembershipModel
)


class OrganizationRepository:

    @classmethod
    async def create_organization(cls, data: dict):

        try:
            async with async_session_factory() as session:

                new_org = OrganizationModel(**data)
                session.add(new_org)
                await session.flush()

                new_org_status = OrganizationStatusHistoryModel(org_id=new_org.id, status_id=1)
                session.add(new_org_status)

                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def read_organizations(cls, field: str, value) -> list[OrganizationModel] | None:
        try:
            async with async_session_factory() as session:
                query = (
                    select(OrganizationModel)
                    .where(getattr(OrganizationModel, field) == value)
                )

                db_response = await session.execute(query)
                organizations = db_response.unique().scalars().all()

                return organizations

        finally:
            await session.close()


class InvitationRepository:

    @classmethod
    async def create_invitation(cls, data: dict):

        try:
            async with async_session_factory() as session:

                session.add(OrganizationInvitationModel(**data))
                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def read_invitations(cls, field: str, value) -> list[OrganizationInvitationModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(OrganizationInvitationModel)
                    .where(
                        and_(
                            getattr(OrganizationInvitationModel, field) == value,
                            OrganizationInvitationModel.expires > func.now()
                        )
                    )
                )

                db_response = await session.execute(query)
                invitations = db_response.unique().scalars().all()

                return invitations

        finally:
            await session.close()

    @classmethod
    async def disable_invitation(cls, invitation_id: int):

        try:
            async with async_session_factory() as session:

                query = (
                    update(OrganizationInvitationModel)
                    .where(OrganizationInvitationModel.id == invitation_id)
                    .values(expires=func.now())
                )

                await session.execute(query)
                await session.commit()

        finally:
            await session.close()


class MembershipRepository:

    @classmethod
    async def create_membership(cls, data: dict):

        try:
            async with async_session_factory() as session:

                session.add(OrganizationMembershipModel(**data))
                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def read_memberships(cls, field: str, value) -> list[OrganizationMembershipModel]:

        try:
            async with async_session_factory() as session:

                query = (
                    select(OrganizationMembershipModel)
                    .where(getattr(OrganizationMembershipModel, field) == value)
                )

                db_response = await session.execute(query)
                invitations = db_response.unique().scalars().all()

                return invitations

        finally:
            await session.close()

    @classmethod
    async def read_current(cls, user_id: int, org_id: int) -> OrganizationMembershipModel:

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
                current = db_response.unique().scalars().one_or_none()

                return current

        finally:
            await session.close()

    @classmethod
    async def read_memberships_of_user(cls, user_id: int) -> list[OrganizationMembershipModel]:

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
                memberships = db_response.unique().scalars().all()

                return memberships

        finally:
            await session.close()

    @classmethod
    async def read_memberships_of_organization(cls, org_id: int) -> list[OrganizationMembershipModel]:

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
                result = db_response.unique().scalars().all()

                return result
        finally:
            await session.close()
