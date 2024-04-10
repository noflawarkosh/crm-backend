from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from auth.router import router as router_auth
from frontend.router import router as router_frontend
from orgs.router import router as router_orgs
from storage.router import router as router_storage

app = FastAPI(title='GreedyBear')
app.mount('/static', StaticFiles(directory='frontend/static'), name='static')

app.include_router(router_auth)
app.include_router(router_orgs)
app.include_router(router_storage)

app.include_router(router_frontend)