import asyncio
from datetime import datetime

import pytz
from aiogram import Bot

from config import ADMINS
from crud.bot_sleep import delete_bot_sleep, get_bot_sleep
from database import async_session

tz = pytz.timezone("Asia/Tashkent")


async def sleep_stop_bot(bot: Bot):
    while True:
        try:
            now_ts = int(datetime.now(tz).timestamp())

            async with async_session() as session:
                bot_sleep = await get_bot_sleep(session)

            if not bot_sleep:
                await asyncio.sleep(60)
                continue

            sleep_time = bot_sleep.sleep_time

            if now_ts >= sleep_time:
                await delete_bot_sleep(session)
                for ADMIN in ADMINS:
                    await bot.send_message(
                        ADMIN,
                        f"Bot sleep vaqti tugadi"
                    )

        except Exception as e:
            for ADMIN in ADMINS:
                await bot.send_message(
                    ADMIN,
                    f"{e}\nsleep_stop.py"
                )

        await asyncio.sleep(60)
