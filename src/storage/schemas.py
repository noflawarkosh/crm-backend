import datetime
from typing import Optional
from pydantic import BaseModel, constr


class StoragePOSTSchema(BaseModel):
    title: constr(max_length=100)
    storage_href: str
    description: Optional[constr(max_length=100)] = None
    type: str
    owner_id: int


class StorageGETSchema(StoragePOSTSchema):
    id: int
    date: datetime.datetime


class StorageFileSchema(BaseModel):
    name: str
    size: int
    content: bytes
    href: str
