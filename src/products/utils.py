import json

import requests

from products.schemas import ProductSizeCreateSchema
from strings import *


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
            'wb_price': size['price']['total'] if size['stocks'] else None
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
