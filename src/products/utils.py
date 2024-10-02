import json
from io import BytesIO

import pandas as pd
import requests

from database import Repository
from picker.utils import parse_excel_lines
from products.models import ProductModel, ReviewModel
from products.schemas import ProductSizeCreateSchema
from strings import *


async def process_reviews_xlsx(file, org_id, stars):
    excel_columns = {
        'wb_article': 0,
        'wb_size_origName': 1,
        'advs': 2,
        'disadvs': 3,
        'text': 4,
        'strict_match': 5,
        'match': 6
    }

    xlsx_reviews_content = await file.read()
    xlsx_reviews = await parse_excel_lines(pd.read_excel(BytesIO(xlsx_reviews_content), dtype=str).values.tolist(),
                                           excel_columns)

    if len(xlsx_reviews) <= 6:
        raise Exception('В файле нет отзывов')

    if len(xlsx_reviews[6:]) > 10000:
        raise Exception('Допустимо не более 10000 отзывов')

    products = await Repository.get_records(
        ProductModel,
        filters=[ProductModel.org_id == org_id],
        select_related=[ProductModel.sizes]
    )

    product_articles = [p.wb_article for p in products]
    records_to_insert = []

    for line in xlsx_reviews[6:]:
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
                        f"Строка {line['line_number']}: не удалось выбрать размер автоматически. Пожалуйста, укажите любой размер товара вручную")
                break

        # Strict match check
        if line['strict_match'] is None:
            raise Exception(f"Строка {line['line_number']}: не указана необходимость в выборе аккаунта")

        try:
            int(str(line['strict_match']).replace(' ', ''))
        except:
            raise Exception(f"Строка {line['line_number']}: необходимость в выборе аккаунта должна быть целым числом")

        strict_match = int(str(line['strict_match']).replace(' ', ''))
        if strict_match not in [0, 1]:
            raise Exception(f"Строка {line['line_number']}: необходимость в выборе аккаунта должна быть 0 или 1")

        # Match check
        if line['match'] is None:
            raise Exception(f"Строка {line['line_number']}: не указано соответствие размеру")

        try:
            int(str(line['match']).replace(' ', ''))
        except:
            raise Exception(f"Строка {line['line_number']}: соответствие размеру должно быть целым числом")

        match = int(str(line['match']).replace(' ', ''))
        if match not in [0, 1, 2, 3]:
            raise Exception(f"Строка {line['line_number']}: соответствие размеру должно быть 0, 1, 2 или 3")

        records_to_insert.append(
            {
                'size_id': selected_size.id,
                'status': 1,
                'text': line['text'],
                'advs': line['advs'],
                'disadvs': line['disadvs'],
                'strict_match': strict_match,
                'match': match,
                'stars': stars,
            }
        )

    await Repository.save_records([{'model': ReviewModel, 'records': records_to_insert}])


def volHostV2(e):
    t = None
    if 0 <= e <= 143:
        t = "01"
    elif 144 <= e <= 287:
        t = "02"
    elif 288 <= e <= 431:
        t = "03"
    elif 432 <= e <= 719:
        t = "04"
    elif 720 <= e <= 1007:
        t = "05"
    elif 1008 <= e <= 1061:
        t = "06"
    elif 1062 <= e <= 1115:
        t = "07"
    elif 1116 <= e <= 1169:
        t = "08"
    elif 1170 <= e <= 1313:
        t = "09"
    elif 1314 <= e <= 1601:
        t = "10"
    elif 1602 <= e <= 1655:
        t = "11"
    elif 1656 <= e <= 1919:
        t = "12"
    elif 1920 <= e <= 2045:
        t = "13"
    elif 2046 <= e <= 2189:
        t = "14"
    elif 2091 <= e <= 2405:
        t = "15"
    elif 2406 <= e <= 2621:
        t = "16"
    else:
        t = "17"
    return f"basket-{t}.wbbasket.ru"


def parse_wildberries_card(url):
    article, picture_data, sizes = None, None, []

    try:
        article = url.split('catalog/')[1].split('/detail.aspx')[0]

    except Exception:
        raise Exception(string_product_parsing_url_error)

    try:
        products_response = (
            requests.get(f'https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}')
        )

        data = json.loads(products_response.text)

    except Exception:
        raise Exception(string_product_products_response_error)

    if not data['data']['products']:
        raise Exception(string_product_products_response_empty)

    for size in data['data']['products'][0]['sizes']:
        sizes.append(ProductSizeCreateSchema.model_validate({
            'wb_size_name': None if size['name'] == '' else size['name'],
            'wb_size_origName': None if size['origName'] == '0' else size['origName'],
            'wb_size_optionId': size['optionId'],
            'wb_in_stock': True if size['stocks'] else False,
            'wb_price': size['price']['total'] if size['stocks'] else None,
            'barcode': None,
            'is_active': True,
        }))

    try:
        picture_response = (
            requests.get(f'https://'
                         f'{volHostV2(int(article) // 100000)}'
                         f'/vol{article[0:-5]}'
                         f'/part{article[0:-3]}'
                         f'/{article}'
                         f'/images/c246x328/1.webp')
        )

        if picture_response.status_code == 200:
            picture_data = picture_response.content

    finally:
        pass

    return data['data']['products'][0]['name'], article, sizes, picture_data
