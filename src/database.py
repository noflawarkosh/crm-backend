from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, selectinload
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

async_engine = create_async_engine(url=DATABASE_URL)
async_session_factory = async_sessionmaker(async_engine)


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
    async def get_records(cls, model, filters=None, select_models=None, less_than=None, greater_than=None):
        """
        :param model: class
        :param filters: {field: value, ...}
        :param select_models: [class.field, ...]
        :return: list[class]
        """
        try:
            async with async_session_factory() as session:
                query = select(model)

                if filters:
                    for filter_field, filter_value in filters.items():
                        query = query.where(getattr(model, filter_field) == filter_value)

                if less_than:
                    for filter_field, filter_value in less_than.items():
                        query = query.where(getattr(model, filter_field) < filter_value)

                if greater_than:
                    for filter_field, filter_value in greater_than.items():
                        query = query.where(getattr(model, filter_field) > filter_value)

                if select_models:
                    for select_model in select_models:
                        query = query.options(selectinload(select_model))

                result = await session.execute(query)
                records = result.scalars().all()
                return records
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
