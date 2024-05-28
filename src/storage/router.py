import os
import shutil
from typing import Annotated
from fastapi import APIRouter, Depends, Response, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from auth.models import UserModel
from auth.utils import authed
from storage.repository import StorageRepository
from storage.schemas import StorageGETSchema, StoragePOSTSchema
from storage.utils import generate_filename, autosave_file
from strings import *

from io import BytesIO
from PIL import Image

router = APIRouter(
    prefix="/storage",
    tags=["Storage"]
)

OTHER_TYPES = []
IMAGE_TYPES = ['jpg', 'jpeg', 'png']
VIDEO_TYPES = ['mp4', 'mov']

OTHER_MAX_SIZE = 10485760  # 10485760  B  =  10  MB
IMAGE_MAX_SIZE = 15728640  # 15728640  B  =  15  MB
VIDEO_MAX_SIZE = 104857600  # 104857600 B  =  100 MB

LOCAL_STORAGE_PATH = 'storage/files'


@router.post('/save')
async def save(user: UserModel = Depends(authed),
               file: UploadFile = File(...)
               ) -> StorageGETSchema:
    """
    Saving file with uploading filename as title without description
    to local storage and creating storage record in db. Compressing file if image
    :param user: identified user by cookie token (strictly authed)
    :param file: uploading file
    :return: storage get schema
    """

    try:
        storage_record = await autosave_file(file, user)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    dto = StorageGETSchema.model_validate(storage_record, from_attributes=True)

    return dto


@router.get('/get/{href}')
async def get_by_href(href: str,
                      user: UserModel = Depends(authed)):
    """
    Default get with filename (href)
    :param href: string like J8iru862AcQ4dNlx.pdf
    :param user: identified user by cookie token (strictly authed)
    :return: file
    """

    file_path = f'{LOCAL_STORAGE_PATH}/{href}'

    if os.path.exists(file_path):
        return FileResponse(path=file_path)

    raise HTTPException(status_code=404)


@router.get('/getById/{record_id}')
async def get_by_record_id(record_id: int,
                           user: UserModel = Depends(authed)):
    """
    Getting file by storage record id. Only for file owner
    :param record_id: storage record identifier
    :param user: identified user by cookie token (strictly authed)
    :return: file
    """

    record = await StorageRepository.get_record_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404)

    if record.owner_id != user.id:
        raise HTTPException(status_code=403)

    file_path = f'{LOCAL_STORAGE_PATH}/{record.storage_href}'

    if os.path.exists(file_path):
        return FileResponse(path=file_path)

    else:
        raise HTTPException(status_code=404)


@router.get('/getOwned')
async def get_all_users_files(user: UserModel = Depends(authed)
                              ) -> list[StorageGETSchema]:
    """
    Getting all user's files
    :param user: identified user by cookie token (strictly authed)
    :return: list if storage record get chemas
    """

    records = await StorageRepository.get_records_by_owner_id(user.id)
    dto = [StorageGETSchema.model_validate(record, from_attributes=True) for record in records]

    return dto
