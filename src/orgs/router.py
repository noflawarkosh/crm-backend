import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, HTTPException

from sqlalchemy import select, delete, update, text, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from auth.models import UserModel
from auth.utils import authed
from database import get_async_session, check_field_is_unique
from orgs.schemas import OrganizationPOSTSchema, OrganizationRELSchema, OrganizationGETSchema, \
    OrganizationInvitationPOSTSchema
from orgs.models import OrganizationModel, OrganizationStatusHistoryModel, OrganizationStatusModel, \
    OrganizationInvitationModel, OrganizationMembershipModel
from orgs.utils import generate_invitation_code

router = APIRouter(
    prefix="/orgs",
    tags=["Organizations"]
)


@router.post('/register')
async def create_organization(request: Request,
                              data: Annotated[OrganizationPOSTSchema, Depends()],
                              user: UserModel = Depends(authed),
                              session: AsyncSession = Depends(get_async_session)):
    data_dict = data.model_dump()

    if not await check_field_is_unique(session, OrganizationModel.inn, data.inn):
        return {'result': 'error', 'details': 'Указанный ИНН уже зарегистрирован'}

    new_org = OrganizationModel(**data_dict)
    new_org.owner_id = user.id
    session.add(new_org)
    await session.flush()

    new_org_status = OrganizationStatusHistoryModel(org_id=new_org.id, status_id=1)
    session.add(new_org_status)
    await session.commit()

    return {'result': 'success', 'details': 'Успешная регистрация'}


@router.get('/getMyOrgs')
async def get_all_user_organizations(request: Request,
                                     user: UserModel = Depends(authed),
                                     session: AsyncSession = Depends(get_async_session)):
    query = (
        select(OrganizationModel)
        .options(selectinload(OrganizationModel.statuses))
        .where(OrganizationModel.owner_id == user.id)
    )

    db_response = await session.execute(query)
    result = db_response.scalars().all()
    dto = [OrganizationRELSchema.model_validate(row, from_attributes=True) for row in result]

    return dto


@router.get('/getOrg/{org_id}')
async def get_organization_by_id(request: Request,
                                 org_id: int,
                                 user: UserModel = Depends(authed),
                                 session: AsyncSession = Depends(get_async_session)):
    query = (
        select(OrganizationModel)
        .options(selectinload(OrganizationModel.statuses))
        .where(OrganizationModel.id == org_id)
    )

    db_response = await session.execute(query)
    organization = db_response.scalars().one_or_none()

    if organization:
        if organization.owner_id == user.id:
            return OrganizationRELSchema.model_validate(organization, from_attributes=True)
        else:
            raise HTTPException(status_code=403, detail='Доступ запрещен')
    else:
        raise HTTPException(status_code=404, detail='Запрашиваемая организация не найдена')


@router.post('/createInvitation/{org_id}')
async def create_invitation(request: Request,
                            data: Annotated[OrganizationInvitationPOSTSchema, Depends()],
                            org_id: int,
                            user: UserModel = Depends(authed),
                            session: AsyncSession = Depends(get_async_session)):
    query = (select(OrganizationModel).where(OrganizationModel.id == org_id))
    db_response = await session.execute(query)
    organization = db_response.scalars().one_or_none()

    if organization:
        if organization.owner_id == user.id:

            data_dict = data.model_dump()
            data_dict['code'] = generate_invitation_code()
            data_dict['org_id'] = organization.id
            new_invitation = OrganizationInvitationModel(**data_dict)
            session.add(new_invitation)
            await session.commit()

            return {'result': 'success', 'details': 'Приглашение создано'}

        else:
            raise HTTPException(status_code=403, detail='Доступ запрещен')
    else:
        raise HTTPException(status_code=404, detail='Запрашиваемая организация не найдена')


@router.post('/acceptInvitation')
async def accept_invitation(request: Request,
                            code: str,
                            user: UserModel = Depends(authed),
                            session: AsyncSession = Depends(get_async_session)):
    query = (
        select(OrganizationInvitationModel)
        .where(
            and_(
                OrganizationInvitationModel.code == code,
                OrganizationInvitationModel.expires > func.NOW()
            )
        )
    )

    db_response = await session.execute(query)
    invitation = db_response.scalars().one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail='Приглашение не найдено или истекло')

    query = (
        select(OrganizationMembershipModel)
        .where(
            OrganizationMembershipModel.invitation_id == invitation.id
        )
    )

    db_response = await session.execute(query)
    invitation_usages = db_response.scalars().all()

    if len(invitation_usages) >= invitation.amount:
        raise HTTPException(status_code=403, detail='Приглашение использовано максимальное кол-во раз')

    query = (
        select(OrganizationModel)
        .where(OrganizationModel.id == invitation.org_id)
    )

    db_response = await session.execute(query)
    organization = db_response.scalars().one_or_none()

    if not organization:
        raise HTTPException(status_code=404, detail='Организация не найдена или ее работа приостановлена')

    if organization.owner_id == user.id:
        raise HTTPException(status_code=403, detail='Вы являетесь владельцем этой организации')

    query = (
        select(OrganizationMembershipModel)
        .where(
            and_(
                OrganizationMembershipModel.user_id == user.id,
                OrganizationMembershipModel.org_id == organization.id
            )
        )
        .order_by(OrganizationMembershipModel.date.desc())
        .limit(1)
    )

    db_response = await session.execute(query)
    current_membership = db_response.scalars().one_or_none()

    if current_membership:
        if current_membership.status_id == 1:
            raise HTTPException(status_code=403, detail='Вы уже являетесь участником этой организации')
        if current_membership.status_id == 4:
            raise HTTPException(status_code=403, detail='Вы были заблокированы владельцем организации')

    new_membership_dict = {
        'org_id': organization.id,
        'user_id': user.id,
        'level': invitation.level,
        'status_id': 1,
        'invitation_id': invitation.id
    }

    new_membership = OrganizationMembershipModel(**new_membership_dict)
    session.add(new_membership)
    await session.commit()

    return {'result': 'success', 'details': 'Приглашение успешно принято'}





@router.get('/getActiveMembershipOrgs')
async def get_user_membership_organizations(request: Request,
                                            user: UserModel = Depends(authed),
                                            session: AsyncSession = Depends(get_async_session)):
    subq = (
        select(
            OrganizationMembershipModel.org_id,
            func.max(OrganizationMembershipModel.date).label('max_date')
        )
        .where(OrganizationMembershipModel.user_id == user.id)
        .group_by(OrganizationMembershipModel.org_id)
        .alias()
    )

    query = (
        select(OrganizationMembershipModel.org_id, OrganizationMembershipModel.status_id)
        .select_from(OrganizationMembershipModel)
        .join(subq, and_(
            OrganizationMembershipModel.org_id == subq.c.org_id,
            OrganizationMembershipModel.date == subq.c.max_date
        ))
        .where(OrganizationMembershipModel.user_id == user.id)
    )

    db_response = await session.execute(query)
    orgs_users_statuses = db_response.all()

    list_of_orgs = []
    for line in orgs_users_statuses:
        if line[1] == 1:
            query = select(OrganizationModel).where(OrganizationModel.id == line[0])
            db_response = await session.execute(query)
            organization = db_response.scalars().one_or_none()
            if organization:
                list_of_orgs.append(OrganizationGETSchema.model_validate(organization, from_attributes=True))

    return list_of_orgs


