from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from auth.models import UserSessionModel
from auth.schemas import UserReadSchema
from auth.router import every
from admin.router import every as admin_every
from database import DefaultRepository
from orgs.models import OrganizationModel
from orgs.repository import MembershipRepository
from payments.models import BalanceBillModel

router = APIRouter()

templates = Jinja2Templates(directory='frontend/templates')

sections = {
    'dashboard': 0,
    'wallet': 0,
    'loyalty': 0,
    'products': 2,
    'tasks': 4,
    'reviews': 8,
    'orders': 16,
}


@router.get('/admin')
async def page(request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if not admin:
        return RedirectResponse('/admin-login')

    return templates.TemplateResponse('admin-dashboard.html', {'request': request})


@router.get('/admin-login')
async def page(request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if admin:
        return RedirectResponse('/admin')

    return templates.TemplateResponse('admin-login.html', {'request': request})


@router.get('/admin-tables-{table}')
async def page(table: str,
               request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if not admin:
        return RedirectResponse('/admin-login')

    return templates.TemplateResponse(f'admin-tables-{table}.html', {'request': request})


@router.get('/admin-scripts/{script}')
async def page(script: str,
               request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if not admin:
        return RedirectResponse('/admin-login')

    return templates.TemplateResponse(f'admin-scripts-{script}.html', {'request': request})


@router.get('/admin-{action}/{table}/{id}')
async def page(action: str,
               request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if not admin:
        return RedirectResponse('/admin-login')

    return templates.TemplateResponse(f'admin-record-{action}.html', {'request': request})


@router.get('/admin-{action}/{table}')
async def page(action: str,
               request: Request,
               admin: UserReadSchema = Depends(admin_every)):
    if not admin:
        return RedirectResponse('/admin-login')

    return templates.TemplateResponse(f'admin-record-{action}.html', {'request': request})


# AUTH PAGES
@router.get('/')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if session:
        return RedirectResponse('/dashboard')

    return RedirectResponse('/login')


@router.get('/register')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if session:
        return RedirectResponse('/dashboard')

    return templates.TemplateResponse('auth-register.html', {'request': request})


@router.get('/login')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if session:
        return RedirectResponse('/dashboard')

    return templates.TemplateResponse('auth-login.html', {'request': request})


@router.get('/success')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if session:
        return RedirectResponse('/dashboard')

    return templates.TemplateResponse('auth-success.html', {'request': request})


# PRIMARY PAGES
@router.get('/dashboard')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if not session:
        return RedirectResponse('/login')

    return templates.TemplateResponse('general-dashboard.html', {'request': request})


@router.get('/organization/{section}/{org_id}')
async def page(request: Request,
               section: str,
               org_id: int,
               session: UserSessionModel = Depends(every)):
    if not session:
        return RedirectResponse('/login')

    organizations = await DefaultRepository.get_records(OrganizationModel, filters={'id': org_id})

    if len(organizations) != 1:
        return RedirectResponse('/404')

    organization = organizations[0]

    if section in sections:
        if organization.owner_id != session.user.id:
            membership = await MembershipRepository.read_current(session.user.id, org_id)
            if not membership or membership.status != 1 or not (membership.level & sections[section]):
                return RedirectResponse('/403')

        return templates.TemplateResponse(f'orgs-{section}.html', {'request': request})

    return RedirectResponse('/404')


# SUBPAGES
@router.get('/bill/{bill_id}')
async def page(request: Request,
               bill_id: int,
               session: UserSessionModel = Depends(every)):
    if not session.user:
        return RedirectResponse('/login')

    bills = await DefaultRepository.get_records(BalanceBillModel, filters={'id': bill_id})

    if len(bills) != 1:
        return RedirectResponse('/404')

    bill = bills[0]

    organizations = await DefaultRepository.get_records(OrganizationModel, filters={'id': bill.org_id})

    if len(organizations) != 1:
        return RedirectResponse('/404')

    organization = organizations[0]

    if organization.status != 2:
        return RedirectResponse('/403')

    if organization.owner_id != session.user.id:
        return RedirectResponse('/403')

    return templates.TemplateResponse('payments-bill.html', {'request': request})


@router.get('/profile')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if not session.user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('user-profile.html', {'request': request})


@router.get('/settings')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if not session.user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('user-settings-general.html', {'request': request})


# UTILITY PAGES
@router.get('/403')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if not session.user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('misc-403.html', {'request': request})


@router.get('/404')
async def page(request: Request,
               session: UserSessionModel = Depends(every)):
    if not session.user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('misc-404.html', {'request': request})

