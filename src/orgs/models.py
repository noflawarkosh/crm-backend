from typing import Annotated
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from auth.models import Base

pk = Annotated[int, mapped_column(primary_key=True)]
dt = Annotated[datetime.datetime, mapped_column(server_default=text('NOW()'))]


class OrganizationModel(Base):
    __tablename__ = 'organization'

    id: Mapped[pk]
    title: Mapped[str]
    inn: Mapped[str]
    owner_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))

    statuses: Mapped[list['OrganizationStatusHistoryModel']] = relationship()


class OrganizationStatusModel(Base):
    __tablename__ = 'organization_status'

    id: Mapped[pk]
    title: Mapped[str]


class OrganizationStatusHistoryModel(Base):
    __tablename__ = 'organization_status_history'

    id: Mapped[pk]
    org_id: Mapped[int] = mapped_column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE'))
    status_id: Mapped[int] = mapped_column(ForeignKey('organization_status.id', ondelete='CASCADE', onupdate='CASCADE'))
    description: Mapped[str | None]
    date: Mapped[dt]

    status: Mapped[OrganizationStatusModel] = relationship(lazy=False)


class OrganizationMembershipModel(Base):
    __tablename__ = 'organization_membership'

    id: Mapped[pk]
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    org_id: Mapped[int] = mapped_column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE'))
    date: Mapped[dt]
    level: Mapped[int]
    status_id: Mapped[int] = mapped_column(ForeignKey('organization_membership_status.id', ondelete='CASCADE', onupdate='CASCADE'))
    invitation_id: Mapped[int | None] = mapped_column(ForeignKey('organization_invitation.id', ondelete='CASCADE', onupdate='CASCADE'))

    organization: Mapped['OrganizationModel'] = relationship()

class OrganizationMembershipStatusModel(Base):
    __tablename__ = 'organization_membership_status'

    id: Mapped[pk]
    title: Mapped[str]


class OrganizationInvitationModel(Base):
    __tablename__ = 'organization_invitation'

    id: Mapped[pk]
    org_id: Mapped[int] = mapped_column(ForeignKey('organization.id', ondelete='CASCADE', onupdate='CASCADE'))
    code: Mapped[str]
    level: Mapped[int]
    created: Mapped[dt]
    expires: Mapped[datetime.datetime | None]
    amount: Mapped[int | None]



"""
class BalanceActionModel(Base):
    __tablename__ = 'balance_action'
    id: Mapped[pk]
    title: Mapped[str]


class BalanceHistoryModel(Base):
    __tablename__ = 'balance_history'

    id: Mapped[pk]
    action_id: Mapped[int]
    org_id: Mapped[int]
    amount: Mapped[float]


class BalanceRequest(Base):
    __tablename__ = 'balance_request'

    id: Mapped[pk]
    org_id: Mapped[int]
    amount: Mapped[float]
    source_id: Mapped[int]


class BalanceRequestMedia(Base):
    __tablename__ = 'balance_request_media'

    id: Mapped[pk]
    request_id: Mapped[int]
    media_id: Mapped[int]


class BalanceSource(Base):
    __tablename__ = 'balance_source'
    id: Mapped[pk]
    title: Mapped[str]
    description: Mapped[str]
    number: Mapped[str]
    is_active: Mapped[bool]
"""