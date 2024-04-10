from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr


class StorageSchema(BaseModel):
    id: Optional[int] = None
    title: constr(max_length=100)
    description: constr(max_length=100)
    storage_href: str
    type: int



