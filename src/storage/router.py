from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session


router = APIRouter(
    prefix="/storage",
    tags=["Storage"]
)



