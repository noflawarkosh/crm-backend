from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from auth.models import UserModel
from auth.router import authed
from strings import *

router_tasks = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

router_orders = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


