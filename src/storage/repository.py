from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from database import async_session_factory

from storage.models import StorageModel
from storage.schemas import StoragePOSTSchema
from strings import *


class StorageRepository:

    @classmethod
    async def save(cls, data: StoragePOSTSchema) -> StorageModel:

        """
        Insertion information about file
        :param data: schema of file info
        :return: storage record ORM
        """

        try:

            async with async_session_factory() as session:

                data_dict = data.model_dump()

                record = StorageModel(**data_dict)
                session.add(record)

                await session.commit()
                await session.refresh(record)

                return record

        finally:
            await session.close()

    @classmethod
    async def get_record_by_id(cls, storage_id: int) -> StorageModel:

        """
        Getting informaation about file by record identifier
        :param storage_id: identifier of storage record
        :return: storage record ORM
        """

        try:
            async with async_session_factory() as session:

                query = (
                    select(StorageModel)
                    .where(StorageModel.id == storage_id)
                )

                db_response = await session.execute(query)
                result = db_response.scalars().one_or_none()

                return result

        finally:
            session.close()

    @classmethod
    async def get_records_by_owner_id(cls, owner_id: int) -> list[StorageModel]:

        """
        Get list of storage records owned by user
        :param owner_id: identifier of user as owner_id
        :return: list of storage ORMs
        """

        try:
            async with async_session_factory() as session:

                query = (
                    select(StorageModel)
                    .where(StorageModel.owner_id == owner_id)
                )

                db_response = await session.execute(query)
                return db_response.scalars().all()

        finally:
            await session.close()
