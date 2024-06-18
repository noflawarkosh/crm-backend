import pandas as pd
from io import BytesIO
from admin.repository import AdminRepository
import datetime
from strings import *


def detect_date(string_date):
    result = None
    if str(string_date) != 'nan':

        if len(string_date) == 19:
            date_format = '%Y-%m-%d %H:%M:%S'
        else:
            string_date = string_date.replace(' ', '')
            date_format = '%d.%m.%Y'

        result = datetime.datetime.strptime(string_date, date_format)

    return result


async def refresh_orders_by_id(data, servers):
    orders = []
    for server in servers:
        ordered_orders_content = await data[f'ordered-{server.id}'].read()
        ordered_orders = pd.read_excel(BytesIO(ordered_orders_content), dtype=str).values.tolist()

        for order in ordered_orders:
            orders.append(
                {
                    'description': str(order[10]),
                    'wb_uuid': str(order[12]),
                    'id': int(order[16]),
                    'wb_price': str(order[14]),
                    'account': str(order[11]),
                }
            )

        db_accounts = await AdminRepository.read_records('OrdersAccountModel')
        db_orders = await AdminRepository.read_records('OrdersOrderModel')

        orders_without_accounts = []
        orders_to_update = []
        orders_not_found = []

        for order in orders:
            existing_account = None
            existing_order = None

            for db_account in db_accounts:
                if order['account'] == db_account.number:
                    existing_account = db_account

            if not existing_account:
                orders_without_accounts.append(order)
                continue

            for db_order in db_orders:
                if order['id'] == db_order.id:
                    existing_order = db_order

            if existing_order and not existing_order.dt_ordered:

                description = order['description']
                dt_ordered = None
                account_id = None
                wb_uuid = None

                if 'Все артикулы заказаны' in order['description']:
                    dt_ordered = datetime.datetime.strptime(
                        order['description'].split('Все артикулы заказаны ')[1],
                        '%d.%m.%Y %H:%M:%S'
                    )
                    description = 'Все артикулы заказаны'
                    account_id = existing_account.id

                    if ',' in wb_uuid:
                        wb_uuid = order['wb_uuid'].replace(' ', '').split(',')[-1]
                    else:
                        wb_uuid = order['wb_uuid']

                orders_to_update.append({
                    'id': existing_order.id,
                    'dt_ordered': dt_ordered,
                    'account_id': account_id,
                    'description': description,
                    'wb_uuid': wb_uuid,
                })

            else:
                orders_not_found.append(order)

        for order in orders_to_update:
            pass



async def refresh_orders_by_uuid(data, servers):
    orders = []
    for server in servers:
        active_orders_content = await data[f'active-{server.id}'].read()
        collected_orders_content = await data[f'collected-{server.id}'].read()

        active_orders = pd.read_excel(BytesIO(active_orders_content), dtype=str).values.tolist()
        collected_orders = pd.read_excel(BytesIO(collected_orders_content), dtype=str).values.tolist()

        for order in active_orders + collected_orders:
            orders.append(
                {
                    'address': str(order[0]),
                    'status': str(order[1]),
                    'name': str(order[2]),
                    'telnum': str(order[3]),
                    'code': str(order[4]),
                    'organization': str(order[5]),
                    'article': str(order[6]),
                    'size': str(order[7]),
                    'product': str(order[8]),
                    'price': str(order[9]),
                    'dt_ordered': str(order[10]),
                    'dt_delivered': str(order[11]),
                    'dt_collected': str(order[12]),
                    'account': str(order[13]),
                    'wb_uuid': str(order[14]),
                    'server_id': server.id,
                }
            )

    db_accounts = await AdminRepository.read_records('OrdersAccountModel')
    db_orders = await AdminRepository.read_records('OrdersOrderModel')

    orders_to_update = []
    orders_to_insert = []

    orders_without_accounts = []

    for order in reversed(orders):

        existing_account = None
        existing_order = None

        for db_account in db_accounts:
            if order['account'] == db_account.number:
                existing_account = db_account

        if not existing_account:
            orders_without_accounts.append(order['account'])
            continue

        for db_order in db_orders:
            if order['wb_uuid'] == db_order.wb_uuid:
                existing_order = db_order

        if existing_order:
            orders_to_update.append({
                'id': existing_order.id,
                'dt_ordered': detect_date(order['dt_ordered']),
                'dt_delivered': detect_date(order['dt_delivered']),
                'dt_collected': detect_date(order['dt_collected']),
                'account_id': existing_account.id,
            })
        else:
            orders_to_insert.append({
                'dt_ordered': detect_date(order['dt_ordered']),
                'dt_delivered': detect_date(order['dt_delivered']),
                'dt_collected': detect_date(order['dt_collected']),
                'account_id': existing_account.id,
            })

    for order in orders_to_insert:
        await AdminRepository.create_record('OrdersOrderModel', order)


async def generate_plan(data):
    bad_accounts = (
        data['bad_accounts'].replace('\n', '').replace(' ', '').split('\r')
        if data.get('bad_accounts', None)
        else []
    )

    db_settings = await AdminRepository.read_records('PickerSettingsModel')
    db_orders = await AdminRepository.read_records('OrdersOrderModel')
    db_servers = await AdminRepository.read_records('OrdersServerModel')

    settings_last_order = datetime.timedelta(days=db_settings.lo)
    settings_account_life = datetime.timedelta(days=db_settings.al)
    settings_now = datetime.datetime.now()
    settings_now_date = settings_now.replace(minute=0, second=0, microsecond=0, hour=0)

    df_orders = pd.DataFrame(
        {
            'org_id': order.org_id,
            'account_id': order.account.id,
            'address_id': order.account.address_id,
            'dt_planed': order.dt_planed,
            'dt_ordered': order.dt_ordered,
            'dt_delivered': order.dt_delivered,
            'dt_collected': order.dt_collected,
        }
        for order in db_orders
    )

    for server in db_servers:

        db_accounts = await AdminRepository.read_records('OrdersAccountModel', filtration={'server_id': server.id})
        db_tasks = []  # TODO

        # common pool
        for account in db_accounts:

            # account active, account address active, account number not in bad_accounts
            if account.number in bad_accounts or not account.is_active or not account.address.is_active:
                continue

            # account last order
            query = (
                df_orders
                .query(f"account_id == {account.id} and dt_collected.isnull()")
                .sort_values('dt_ordered', ascending=True)
                .head(1)
            )

            last_order = query['dt_ordered'].iloc[0] if len(query.values) != 0 else None

            if last_order and last_order + settings_last_order < settings_now_date:
                continue

            # account registration date
            query = (
                df_orders
                .query(f"account_id == {account.id}")
                .sort_values('dt_ordered', ascending=True)
                .head(1)
            )

            default_reg_date = query['dt_ordered'].iloc[0] if len(query.values) != 0 else settings_now_date
            reg_date = account.reg_dt if account.reg_dt else default_reg_date

            if reg_date + settings_account_life < settings_now_date:
                continue

            # contractor
            contractor = next(
                (
                    contractor for contractor in server.contractors
                    if contractor.id == account.address.contractor.id
                ), None
            )

            if not contractor:
                continue

            T = (df_orders.query(f'account_id == {account.id} and dt_collected.isnull()').shape[0])

            if T not in (contractor.load_t_min, contractor.load_t_max + 1):
                continue

            W = (df_orders.query(f'address_id == {account.address_id} and dt_collected.isnull()').shape[0])

            accs.append({
                'account_id': account.id,
                'address_id': account.address.id,
                'number': account.number,
                'address': account.address.address,
                'contractor': contractor,
                'district': account.address.district,

                'T': T,  # amount of active orders on account
                'W': W,  # amount of active orders on account's address
            })

        # account pick

        for task in tasks:
            amount = tasks[task]

            org_used_accs, org_used_addr, org_accs = [], [], []

            cs_tmp = sorted(server.contractors, key=lambda x: x['percent'], reverse=True)
            contractors = []
            remaining = amount

            for c_tmp in cs_tmp[:-1]:

                cmax = round(amount * c_tmp['percent'])

                if cmax >= remaining:
                    cmax = remaining
                    remaining = 0

                elif cmax < remaining:
                    remaining -= cmax

                contractors.append({
                    'name': c_tmp['name'],
                    'usages': [],
                    'max': cmax
                })

            contractors.append({
                'name': cs_tmp[-1]['name'],
                'usages': [],
                'max': remaining
            })

            for acc in accs:

                I = (df_orders.query(f"account_id == {acc['account_id']} and org == '{org}'").shape[0])
                ws_org[f'K{line}'] = I

                if I != 0:
                    ws_org[f'H{line}'] = 'Исключен, ИП уже заказывал на этот аккаунт'
                    continue

                query = (
                    df_orders
                    .query(f"address_id == {acc['address_id']} and org == '{org}'")
                    .sort_values('dt_ordered', ascending=False)
                    .head(1)
                )

                M = query['dt_ordered'].iloc[0] if len(query.values) != 0 else None

                if M:
                    ws_org[f'L{line}'] = M.strftime('%d.%m.%Y')
                else:
                    ws_org[f'L{line}'] = 'Не найдено'

                if M and M > acc['contractor']['M']:
                    ws_org[f'H{line}'] = 'Исключен, дата последнего заказа вне допустимого интервала'
                    continue

                H = (df_orders.query(f"address_id == {acc['address_id']} and org == '{org}'").shape[0])

                ws_org[f'M{line}'] = H
                org_accs.append({
                    'org': org,
                    **acc,
                    'I': I,
                    'H': H,  # amount of all orders of org on address of account
                    'M': M,  # date of the last purchase of org on account's address
                    'logs': line,
                })

                ws_org[f'H{line}'] = 'Не исключен'

            for i in range(0, amount):

                org_accs = await utils.proc_0(org_accs, used_addrs)  # L | K W

                if not org_accs:
                    break

                org_accs = await utils.proc_1(org_accs)  # X Z AB AD   | H L T
                org_accs = await utils.proc_2(org_accs)  # Y AA AC AE  | X Z AB AD
                org_accs = await utils.proc_3(org_accs)  # AF          | Y AA AC AE

                org_accs = sorted(org_accs, key=lambda x: x['AF'], reverse=True)

                for org_acc in org_accs:

                    if org_acc['address_id'] in org_used_addr:
                        continue

                    # J
                    for contractor in contractors:
                        if (len(contractor['usages']) != contractor['max'] and
                                org_acc['contractor']['name'] == contractor['name']):

                            HH = (
                                df_orders.query(f'address_id == {org_acc["address_id"]} and dt_collected.isnull()').loc[
                                :,
                                'account_id'].unique().shape[0])

                            aa_accs = []
                            JJ = 0
                            for aacc in total_selected_accounts:
                                if aacc['address_id'] == org_acc['address_id'] and aacc['account_id'] not in aa_accs:
                                    aa_accs.append(aacc['account_id'])
                                    JJ += 1

                            II = HH + JJ  # кол во аккаунтов с активными заказами на адресе аккаунта

                            if II >= org_acc['contractor']['I'] and org_acc['T'] == 0:
                                continue

                            J = used_accs[org_acc['contractor']['name']].count(org_acc['account_id'])

                            if J in org_acc['contractor']['J']:
                                org_acc['J'] = J
                                contractor['usages'].append(org_acc['account_id'])
                                used_addrs.append(org_acc['address_id'])
                                used_accs[org_acc['contractor']['name']].append(org_acc['account_id'])
                                org_used_addr.append(org_acc['address_id'])
                                selected_accs.append(org_acc)
                                total_selected_accounts.append(org_acc)

                                ws_org[f'Y{org_acc["logs"]}'] = 'Выбран'
                                fill = PatternFill(patternType='solid', fgColor='FF00FF00')
                                ws_org[f'D{org_acc["logs"]}'].fill = fill

                                break
