from sqlalchemy import select, and_, func, text, update, sql, inspect, delete
from sqlalchemy.orm import selectinload
from storage.models import (
    StorageModel,
)
from admin.models import AdminUserModel, AdminSessionModel
from orgs.models import (
    OrganizationModel,
    OrganizationInvitationModel
)
from admin.schemas import AdminReadSchema, AdminSessionReadSchema, AdminSessionCreateSchema, AdminReadWPSchema
from auth.models import UserModel, UserSessionModel
from products.models import ProductModel
from database import async_session_factory
from orders.models import (
    OrdersServerScheduleModel,
    OrdersServerContractorModel,
    OrdersServerModel,
    OrdersContractorModel,
    OrdersAccountModel,
    OrdersContractorModel,
    OrdersAddressModel,
    OrdersOrderModel,

)
from admin.models import PickerSettingsModel
from payments.models import (
    BalanceHistoryModel,
    BalanceBillStatusModel,
    BalanceBillModel,
    BalanceSourceModel,
    BalanceActionModel
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
    async def save_records(cls, records: dict[str, list[dict]]):
        records_to_update = {}
        records_to_create = {}
        try:
            async with async_session_factory() as session:
                for model_name, model_records in records.items():
                    model = globals().get(model_name, None)
                    if model is None:
                        continue

                    for record in model_records:
                        if 'id' in record:
                            records_to_update.setdefault(model_name, []).append(record)
                        else:
                            records_to_create.setdefault(model_name, []).append(record)

                for model_name, records_to_update_for_model in records_to_update.items():
                    model = globals().get(model_name, None)

                    for record in records_to_update_for_model:
                        query = (
                            update(model)
                            .where(model.id == record['id'])
                            .values(**record)
                        )
                        await session.execute(query)

                for model_name, records_to_create_for_model in records_to_create.items():
                    model = globals().get(model_name, None)

                    for record in records_to_create_for_model:
                        session.add(model(**record))

                await session.commit()
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
                                    if isinstance(field.type, sql.sqltypes.Boolean):
                                        values = [bool(value) for value in values]

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
    async def read_fields(cls, model: str):
        model = globals().get(model)
        mapper = inspect(model)
        fields = {}
        for column in mapper.columns:
            fields[column.name] = str(column.type)

        return fields

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
