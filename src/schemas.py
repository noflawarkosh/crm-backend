from pydantic import BaseModel


class ResponseSchema(BaseModel):

    detail: str

