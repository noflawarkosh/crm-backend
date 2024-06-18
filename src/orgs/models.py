from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime

from auth.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


# Organization
class OrganizationModel(Base):
    __tablename__ = 'organization'

    id: Mapped[pk]
    title: Mapped[str]
    inn: Mapped[str]

    # FK
    owner_id: Mapped[int] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    statuses: Mapped[list['OrganizationStatusHistoryModel']] = relationship(lazy=False)
    owner: Mapped['UserModel'] = relationship(lazy=False)


class OrganizationStatusModel(Base):
    __tablename__ = 'organization_status'

    id: Mapped[pk]
    title: Mapped[str]


class OrganizationStatusHistoryModel(Base):
    __tablename__ = 'organization_status_history'

    id: Mapped[pk]
    description: Mapped[str | None]
    date: Mapped[dt]

    # FK
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey('organization_status.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    status: Mapped[OrganizationStatusModel] = relationship(lazy=False)


# Membership
class OrganizationMembershipModel(Base):
    __tablename__ = 'organization_membership'

    id: Mapped[pk]
    date: Mapped[dt]
    level: Mapped[int]

    # FK
    user_id: Mapped[int] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey('organization_membership_status.id', ondelete='CASCADE', onupdate='CASCADE')
    )
    invitation_id: Mapped[int | None] = mapped_column(
        ForeignKey('organization_invitation.id', ondelete='CASCADE', onupdate='CASCADE')
    )

    # Relationships
    user: Mapped['UserModel'] = relationship(lazy=False)
    status: Mapped['OrganizationMembershipStatusModel'] = relationship(lazy=False)
    invitation: Mapped['OrganizationInvitationModel'] = relationship(lazy=False)
    organization: Mapped['OrganizationModel'] = relationship(lazy=False)


class OrganizationMembershipStatusModel(Base):
    __tablename__ = 'organization_membership_status'

    id: Mapped[pk]
    title: Mapped[str]


# Invitation
class OrganizationInvitationModel(Base):
    __tablename__ = 'organization_invitation'

    id: Mapped[pk]
    code: Mapped[str]
    level: Mapped[int]
    created: Mapped[dt]
    expires: Mapped[datetime.datetime | None]
    amount: Mapped[int | None]

    # FK
    org_id: Mapped[int] = mapped_column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE'))
    usages: Mapped[list['OrganizationMembershipModel']] = relationship(
        primaryjoin="and_(OrganizationInvitationModel.id == OrganizationMembershipModel.invitation_id)", lazy=False)
