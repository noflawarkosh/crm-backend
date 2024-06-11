from sqlalchemy import select, and_, func, text, update, sql, inspect
from sqlalchemy.orm import selectinload
from storage.models import (
    StorageModel,
)
from admin.models import AdminUserModel, AdminSessionModel
from orgs.models import (OrganizationModel)
from admin.schemas import AdminReadSchema, AdminSessionReadSchema, AdminSessionCreateSchema, AdminReadWPSchema
from auth.models import UserStatusHistoryModel, UserModel
from products.models import ProductModel
from database import async_session_factory
from orders.models import (
    OrdersServerScheduleModel,
    OrdersServerContractorModel,
    OrdersServerModel,
    OrdersContractorModel

)


class AdminRepository:

    @classmethod
    async def read_admin_by_attribute(cls, field: str, value: str, wp: bool = False):

        try:

            async with async_session_factory() as session:

                query = (
                    select(AdminUserModel)
                    .where(getattr(AdminUserModel, field) == value)
                )

                db_response = await session.execute(query)
                admin = db_response.scalars().one_or_none()

                if admin:

                    if wp:
                        return AdminReadWPSchema.model_validate(admin, from_attributes=True)

                    return AdminReadSchema.model_validate(admin, from_attributes=True)

        finally:
            await session.close()

    @classmethod
    async def read_admin_by_token(cls, token: str) -> AdminReadSchema | None:

        try:
            async with async_session_factory() as session:

                query = (
                    select(AdminSessionModel)
                    .where(
                        and_(
                            AdminSessionModel.token == token,
                            AdminSessionModel.expires > func.now()
                        )
                    )
                    .limit(1)
                )

                db_response = await session.execute(query)
                admin_session = db_response.unique().scalars().one_or_none()

                if not admin_session:
                    return None

                query = (
                    select(AdminUserModel)
                    .where(AdminUserModel.id == admin_session.user_id)
                    .limit(1)
                )

                db_response = await session.execute(query)
                admin = db_response.unique().scalars().one_or_none()

                return AdminReadSchema.model_validate(admin, from_attributes=True) if admin else None

        finally:
            await session.close()

    @classmethod
    async def read_session(cls, token: str):

        try:
            async with async_session_factory() as session:
                query = (
                    select(AdminSessionModel)
                    .where(
                        and_(
                            AdminSessionModel.token == token,
                            AdminSessionModel.expires > func.now()
                        )
                    )
                    .limit(1)
                )

                db_response = await session.execute(query)
                admin_session = db_response.unique().scalars().one_or_none()
                return AdminSessionReadSchema.model_validate(admin_session,
                                                             from_attributes=True) if admin_session else None
        finally:
            await session.close()

    @classmethod
    async def create_session(cls, data: AdminSessionCreateSchema) -> AdminSessionReadSchema:

        try:

            async with async_session_factory() as session:

                admin_session = AdminSessionModel(**data.model_dump())

                session.add(admin_session)
                await session.commit()
                await session.refresh(admin_session)

                return AdminSessionReadSchema.model_validate(admin_session, from_attributes=True)

        finally:
            await session.close()

    @classmethod
    async def update_deactivate_session(cls, token: str):

        try:

            async with async_session_factory() as session:

                query = (
                    update(AdminSessionModel)
                    .where(AdminSessionModel.token == token)
                    .values(expires=func.now())
                )

                await session.execute(query)
                await session.commit()

        finally:
            await session.close()

    @classmethod
    async def read_users_statuses(cls):

        try:

            async with async_session_factory() as session:

                subquery = (
                    select(
                        UserStatusHistoryModel.user_id,
                        func.max(UserStatusHistoryModel.date)
                        .label('latest_date')
                    )
                    .group_by(UserStatusHistoryModel.user_id).subquery()
                )

                query = (
                    select(UserModel.id, UserStatusHistoryModel.status_id)
                    .join(UserStatusHistoryModel, UserModel.id == UserStatusHistoryModel.user_id)
                    .join(subquery, and_(
                        UserStatusHistoryModel.user_id == subquery.c.user_id,
                        UserStatusHistoryModel.date == subquery.c.latest_date
                    ))

                )

                db_response = await session.execute(query)

                return db_response.all()

        finally:
            await session.close()

    @classmethod
    async def read_records(cls, model: str, offset: int = None, limit: int = None, filtration: dict = None):

        model = globals().get(model)
        if model:
            try:
                async with async_session_factory() as session:

                    query = (select(model))

                    if filtration:
                        subquery = and_()

                        for key, values in filtration.items():
                            if values:
                                field = getattr(model, key, None)
                                if field:
                                    if isinstance(field.type, sql.sqltypes.Integer):
                                        values = [int(value) for value in values]

                                    subquery &= getattr(model, key).in_(values)

                        query = query.where(subquery)

                    if offset:
                        query = query.offset(offset)

                    if limit:
                        query = query.limit(limit)

                    db_response = await session.execute(query)
                    records = db_response.unique().scalars().all()

                    return records

            finally:
                await session.close()

    @classmethod
    async def read_counters(cls):

        try:
            async with async_session_factory() as session:
                subquery = (
                    select(
                        UserStatusHistoryModel.user_id,
                        func.max(UserStatusHistoryModel.date)
                        .label('latest_date')
                    )
                    .group_by(UserStatusHistoryModel.user_id).subquery()
                )

                query = (
                    select(UserModel.id, UserStatusHistoryModel.status_id)
                    .join(UserStatusHistoryModel, UserModel.id == UserStatusHistoryModel.user_id)
                    .join(subquery, and_(
                        UserStatusHistoryModel.user_id == subquery.c.user_id,
                        UserStatusHistoryModel.date == subquery.c.latest_date
                    ))
                    .filter(UserStatusHistoryModel.status_id == 1)
                )

                db_response = await session.execute(query)

                new_users = len(db_response.unique().scalars().all())


        finally:
            await session.close()

    @classmethod
    async def read_fields(cls, model: str):
        model = globals().get(model)
        mapper = inspect(model)
        fields = {}
        for column in mapper.columns:
            fields[column.name] = str(column.type)

        return fields

    @classmethod
    async def update_record(cls, model: str, record_id: int, values: dict):

        model = globals().get(model, None)

        if model:
            try:
                async with async_session_factory() as session:
                    query = (
                        update(model)
                        .where(model.id == record_id)
                        .values(**values)
                    )

                    await session.execute(query)
                    await session.commit()

            finally:
                await session.close()

    @classmethod
    async def create_record(cls, model: str, values: dict):
        model = globals().get(model, None)

        if model:

            try:
                async with async_session_factory() as session:

                    record = model(**values)
                    session.add(record)

                    await session.commit()
                    await session.refresh(record)

            finally:
                await session.close()
