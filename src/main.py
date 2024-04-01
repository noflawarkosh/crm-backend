from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from auth.router import router as router_auth
from frontend.router import router as router_frontend

app = FastAPI(title='CRM App')
app.mount('/static', StaticFiles(directory='static'), name='static')
app.include_router(router_auth)
app.include_router(router_frontend)