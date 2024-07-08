import boto3
from sqlalchemy import update, select, delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine , AsyncSession
from sqlalchemy.orm import DeclarativeBase, selectinload, joinedload
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, S3KID, S3KEY


DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

async_engine = create_async_engine(url=DATABASE_URL)
async_session_factory = async_sessionmaker(async_engine)

storage = boto3.session.Session()
s3 = storage.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=S3KID,
    aws_secret_access_key=S3KEY
)


class Base(DeclarativeBase):
    pass


class DefaultRepository:
    @classmethod
    async def save_records(cls, models):
        """
        :param models: [{'model': ,'records': [{}]}]
        :return: None
        """
        try:
            async with async_session_factory() as session:
                records_to_insert = []
                for model in models:
                    for record in model['records']:
                        if record.get('id'):
                            await session.merge(model['model'](**record))
                        else:
                            records_to_insert.append(model['model'](**record))
                session.add_all(records_to_insert)
                await session.flush()
                await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


    @classmethod
    async def update_records(cls, model, records):
        try:
            async with async_session_factory() as session:
                for record in records:
                    query = update(model).where(model.id == record['id']).values(**record)
                    await session.execute(query)

                await session.commit()
        finally:
            await session.close()

    @classmethod
    async def get_records(cls, model, filters=None, joins=None, select_related=None, prefetch_related=None,
                          order_by=None, limit=None, offset=None, selects=None, deep_related=None, filtration=None):

        try:
            async with async_session_factory() as session:

                if selects:
                    query = select(model, *selects)
                else:
                    query = select(model)

                if filters:
                    for condition in filters:
                        query = query.where(condition)

                if joins:
                    for join in joins:
                        query = query.join(join)

                if select_related:
                    for select_model in select_related:
                        query = query.options(selectinload(select_model))

                if deep_related:
                    for deep_model in deep_related:
                        query = query.options(selectinload(*deep_model))

                if prefetch_related:
                    for prefetch_model in prefetch_related:
                        query = query.options(joinedload(prefetch_model))

                if filtration:
                    for filtration in filtration:
                        query = query.filter(filtration)

                if order_by:
                    query = query.order_by(*order_by)

                if limit:
                    query = query.limit(limit)

                if offset:
                    query = query.offset(offset)

                result = await session.execute(query)
                records = result.unique().scalars().all()
                return records

        except Exception as e:
            await session.rollback()
            raise e

        finally:
            await session.close()

    @classmethod
    async def delete_record(cls, model, record_id: int):

        try:
            async with async_session_factory() as session:

                query = (
                    delete(model)
                    .where(model.id == record_id)
                )

                await session.execute(query)
                await session.commit()

        finally:
            await session.close()
