from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import UserModel
from database import get_async_session
from auth.utils import any, authed, not_authed
from orgs.repository import OrganizationRepository, MembershipRepository
from payments.repository import PaymentsRepository

router = APIRouter()

templates = Jinja2Templates(directory='frontend/templates')


@router.get('/')
async def landing_page(request: Request,
                       user: UserModel = Depends(any)):
    if user:
        return RedirectResponse('/dashboard')

    return RedirectResponse('/login')


# AUTH PAGES
@router.get('/register')
async def registration_page(request: Request,
                            user: UserModel = Depends(any)):
    if user:
        return RedirectResponse('/dashboard')

    return templates.TemplateResponse('auth-register.html', {'request': request})


@router.get('/login')
async def login_page(request: Request,
                     user: UserModel = Depends(any)):
    if user:
        return RedirectResponse('/dashboard')

    return templates.TemplateResponse('auth-login.html', {'request': request})


# PRIMARY PAGES
@router.get('/dashboard')
async def dashboard_page(request: Request,
                         user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('general-dashboard.html', {'request': request})


@router.get('/organization/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-dashboard.html', {'request': request})


@router.get('/wallet/{org_id}')
async def wallet_page(request: Request,
                      org_id: int,
                      user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-wallet.html', {'request': request})


@router.get('/loyalty/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-loyalty.html', {'request': request})


@router.get('/products/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        membership = await MembershipRepository.get_current(user.id, org_id)

        if not membership or membership.status_id != 1 or not (membership.level & 2):
            return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-loyalty.html', {'request': request})


@router.get('/tasks/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        membership = await MembershipRepository.get_current(user.id, org_id)

        if not membership or membership.status_id != 1 or not (membership.level & 4):
            return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-loyalty.html', {'request': request})


@router.get('/reviews/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        membership = await MembershipRepository.get_current(user.id, org_id)

        if not membership or membership.status_id != 1 or not (membership.level & 8):
            return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-loyalty.html', {'request': request})


@router.get('/orders/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    organization = await OrganizationRepository.get_one(org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        membership = await MembershipRepository.get_current(user.id, org_id)

        if not membership or membership.status_id != 1 or not (membership.level & 16):
            return RedirectResponse('/403')

    return templates.TemplateResponse('orgs-loyalty.html', {'request': request})


# SUBPAGES
@router.get('/bill/{bill_id}')
async def registration_page(request: Request,
                            bill_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    bill = await PaymentsRepository.get_bill(bill_id)

    if not bill:
        return RedirectResponse('/404')

    organization = await OrganizationRepository.get_one(bill.org_id)

    if not organization:
        return RedirectResponse('/404')

    if organization.owner_id != user.id:
        return RedirectResponse('/403')

    return templates.TemplateResponse('payments-bill.html', {'request': request})


@router.get('/profile')
async def profile_page(request: Request,
                       user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('user-profile.html', {'request': request})


@router.get('/settings')
async def settings_page(request: Request,
                        user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('user-settings-general.html', {'request': request})


# UTILITY PAGES
@router.get('/403')
async def page_403(request: Request,
                   user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('misc-403.html', {'request': request})


@router.get('/404')
async def page_404(request: Request,
                   user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('misc-404.html', {'request': request})
