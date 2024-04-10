from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import UserModel
from database import get_async_session
from auth.utils import any, authed, not_authed

router = APIRouter()

templates = Jinja2Templates(directory='frontend/templates')


@router.get('/test')
async def landing_page(request: Request,
                       user: UserModel = Depends(any)):


    return templates.TemplateResponse('tables-datatables-advanced.html', {'request': request})


@router.get('/')
async def landing_page(request: Request,
                       user: UserModel = Depends(any)):
    if user:
        return RedirectResponse('/dashboard')

    return RedirectResponse('/login')


@router.get('/organization/{org_id}')
async def registration_page(request: Request,
                            org_id: int,
                            user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('orgs-settings.html', {'request': request})


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


@router.get('/dashboard')
async def dashboard_page(request: Request,
                         user: UserModel = Depends(any)):
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse('general-dashboard.html', {'request': request})


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
