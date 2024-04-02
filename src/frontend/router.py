from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from auth.utils import get_user

router = APIRouter(
    prefix='/v1',
    tags=['Frontend']
)

templates = Jinja2Templates(directory='templates')


@router.get('/register')
async def registration_page(request: Request,
                            session: AsyncSession = Depends(get_async_session)):

    user = await get_user(session, request)

    if user:
        return RedirectResponse('/v1/dashboard')

    return templates.TemplateResponse('auth-register.html', {'request': request})


@router.get('/login')
async def registration_page(request: Request,
                            session: AsyncSession = Depends(get_async_session)):

    user = await get_user(session, request)

    if user:
        return RedirectResponse('/v1/dashboard')

    return templates.TemplateResponse('auth-login.html', {'request': request})


@router.get('/dashboard')
async def registration_page(request: Request,
                      session: AsyncSession = Depends(get_async_session)):

    user = await get_user(session, request)
    if not user:
        return RedirectResponse('/v1/login')

    return templates.TemplateResponse('base.html', {'request': request})