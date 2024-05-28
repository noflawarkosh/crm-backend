import random
import string

from strings import *

from storage.repository import StorageRepository
from storage.schemas import StoragePOSTSchema
from io import BytesIO
from PIL import Image

LOCAL_STORAGE_PATH = 'storage/files'
OTHER_TYPES = []
IMAGE_TYPES = ['jpeg', 'png']
VIDEO_TYPES = ['mp4', 'mov']

OTHER_MAX_SIZE = 10485760  # 10485760  B  =  10  MB
IMAGE_MAX_SIZE = 15728640  # 15728640  B  =  15  MB
VIDEO_MAX_SIZE = 52428800  # 52428800  B  =  50  MB


def generate_filename():
    alphanumeric_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric_characters) for _ in range(16))


async def verify_file(file):
    fileinfo = file.name.rsplit('.', maxsplit=1)

    if len(fileinfo) != 2:
        raise Exception(string_storage_wrong_filetype)

    filename = fileinfo[0]
    filetype = fileinfo[1]

    if len(filename) == 0:
        raise Exception(string_storage_empty_filename)

    if not (filetype in OTHER_TYPES or filetype in IMAGE_TYPES or filetype in VIDEO_TYPES):
        raise Exception(string_storage_wrong_filetype)

    if filetype in IMAGE_TYPES and file.size > IMAGE_MAX_SIZE:
        raise Exception(string_storage_max_size)

    if filetype in VIDEO_TYPES and file.size > VIDEO_MAX_SIZE:
        raise Exception(string_storage_max_size)

    if filetype in OTHER_TYPES and file.size > OTHER_MAX_SIZE:
        raise Exception(string_storage_max_size)


async def autosave_file(href, content):
    fileinfo = href.rsplit('.', maxsplit=1)
    filetype = fileinfo[1]

    if filetype in IMAGE_TYPES:

        image = Image.open(BytesIO(content))
        image.seek(0)
        output = BytesIO()

        if len(content) > 1048576:
            quality = 20

        else:
            quality = 70

        image.save(output, format=filetype, quality=quality, optimize=True)

        with open(f'{LOCAL_STORAGE_PATH}/{href}', 'wb') as f:
            f.write(output.getvalue())

    else:

        with open(f'{LOCAL_STORAGE_PATH}/{href}', 'wb') as buffer:
            buffer.write(content)

    return True
