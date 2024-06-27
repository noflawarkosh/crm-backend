from datetime import datetime, timedelta


async def payment_week(created_at):
    current_date = datetime.now()
    current_week = (current_date - created_at).days // 7

    ws = created_at + timedelta(days=current_week * 7)
    we = ws + timedelta(days=7)

    return ws, we, current_week
