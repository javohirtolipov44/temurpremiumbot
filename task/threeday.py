import asyncio
from datetime import datetime

import pytz
from aiogram import Bot

from config import ADMINS
from crud.premium_users import all_premium_users
from database import async_session


tz = pytz.timezone("Asia/Tashkent")

async def three_day(bot: Bot):
    while(True):
        async with async_session() as session:
            all_prem_users = await all_premium_users(session)
        for user in all_prem_users:
            now_day_dt = int(datetime.now(tz).strftime("%d"))
            now_month_dt = int(datetime.now(tz).strftime("%m"))
            now_year_dt = int(datetime.now(tz).strftime("%Y"))
            # now_day_dt = 10
            # now_month_dt = 2
            end_at_day_dt = int(datetime.fromtimestamp(user.end_at, tz).strftime("%d"))
            end_at_month_dt = int(datetime.fromtimestamp(user.end_at, tz).strftime("%m"))
            end_at_year_dt = int(datetime.fromtimestamp(user.end_at, tz).strftime("%Y"))
            start_at_dt = datetime.fromtimestamp(user.start_at, tz)
            end_at_dt = datetime.fromtimestamp(user.end_at, tz)
            start_at = start_at_dt.strftime("%Y-%m-%d %H:%M")
            end_at = end_at_dt.strftime("%Y-%m-%d %H:%M")
            if now_year_dt == end_at_year_dt:
                if now_month_dt == end_at_month_dt:
                    if end_at_day_dt-now_day_dt == 3:
                        try:
                            await bot.send_message(user.chat_id,"<b>Obunangiz tugashiga 3 kun qoldi\n\n"
                                                                    f"⏱ Boshlanish: {start_at}\n"
                                                                    f"⏳ Tugash: {end_at}</b>",
                                                                    parse_mode="HTML")
                        except Exception as e:
                            for ADMIN in ADMINS:
                                await bot.send_message(ADMIN, f"{e}\n\nID : {user.chat_id}\n\nthreeday.py")


        await asyncio.sleep(86400)
