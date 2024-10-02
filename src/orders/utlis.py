import datetime
from io import BytesIO

import pandas as pd

from database import Repository
from orders.models import OrdersOrderModel
from picker.utils import parse_excel_lines, detect_date
from products.models import ProductModel


async def process_order_tasks_xlsx(file, org_id):
    excel_columns = {
        'dt_planed': 0,
        'wb_article': 1,
        'wb_size_origName': 2,
        'wb_keyword': 3,
    }

    xlsx_reviews_content = await file.read()
    xlsx_reviews = await parse_excel_lines(pd.read_excel(BytesIO(xlsx_reviews_content), dtype=str).values.tolist(),
                                           excel_columns)

    if len(xlsx_reviews) == 0:
        raise Exception('В файле нет задач')

    if len(xlsx_reviews) > 10000:
        raise Exception('Допустимо не более 10000 задач')

    products = await Repository.get_records(
        ProductModel,
        filters=[ProductModel.org_id == org_id],
        select_related=[ProductModel.sizes]
    )

    product_articles = [p.wb_article for p in products]
    records_to_insert = []

    for line in xlsx_reviews:
        print(line)
        # Article check
        if not line['wb_article']:
            raise Exception(f"Строка {line['line_number']}: артикул не указан")

        if line['wb_article'].replace(' ', '') not in product_articles:
            raise Exception(f"Строка {line['line_number']}: товар не найден")

        # Size check
        selected_size = None
        for product in products:
            if product.wb_article == line['wb_article']:

                # Search size
                for size in product.sizes:
                    if size.wb_size_origName == line['wb_size_origName']:
                        selected_size = size
                        break

                if line['wb_size_origName'] and not selected_size:
                    raise Exception(f"Строка {line['line_number']}: размер не найден")

                # Size not found
                if not selected_size:
                    if len(product.sizes) == 1 and product.sizes[0].wb_size_origName is None:
                        selected_size = product.sizes[0]
                    else:
                        for size in product.sizes:
                            if size.wb_in_stock and size.barcode:
                                selected_size = size
                                break

                if not selected_size:
                    raise Exception(
                        f"Строка {line['line_number']}: не удалось найти размер")

                if not selected_size.wb_in_stock:
                    raise Exception(f"Строка {line['line_number']}: размер не в наличии")

                if not selected_size.barcode:
                    raise Exception(f"Строка {line['line_number']}: штрих-код размера не указан")

                break

        # dt_planed check
        if line['dt_planed'] is None:
            raise Exception(f"Строка {line['line_number']}: не указана дата задачи")

        dt_planed = detect_date(line['dt_planed'])

        if dt_planed is None:
            raise Exception(f"Строка {line['line_number']}: не удалось распознать дату")

        if dt_planed.date() < datetime.datetime.now().date():
            raise Exception(f"Строка {line['line_number']}: дата задачи должна быть не раньше текущего дня")

        if dt_planed.date() == datetime.datetime.now().date() and datetime.datetime.now().hour >= 9:
            raise Exception(f"Строка {line['line_number']}: задачи на текущий день принимаются до 09:00")

        if line['wb_keyword'] is None:
            raise Exception(f"Строка {line['line_number']}: не указан ключевой запрос")

        records_to_insert.append(
            {
                'size_id': selected_size.id,
                'status': 1,
                'wb_keyword': line['wb_keyword'],
                'dt_planed': dt_planed.date(),
            }
        )

    await Repository.save_records([{'model': OrdersOrderModel, 'records': records_to_insert}])
