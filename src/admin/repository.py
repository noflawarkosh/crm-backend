from sqlalchemy import select, and_, func, text, update, sql, inspect, delete

from database import async_session_factory


class AdminRepository:





    @classmethod
    async def delete_record(cls, model: str, record_id: int):
        model = globals().get(model, None)

        if model:

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

    @classmethod
    async def read_model(cls, model: str):
        model = globals().get(model, None)
        return model
