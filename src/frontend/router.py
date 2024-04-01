from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix='/v1',
    tags=['Frontend']
)

templates = Jinja2Templates(directory='templates')

@router.get('/register')
def registration_page(request: Request):
    return templates.TemplateResponse('auth-register.html', {'request': request})