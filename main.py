from aiogram import Bot, Dispatcher
import asyncio

from config import TOKEN
import logging
import handlers
from database import check_db_connection, create_tables
from middlewares.ban_user import BanUserMiddleware
from middlewares.anti_flood import AntiFloodMiddleware
from task.notify import monthly_admin_notify
from task.sleep_stop import sleep_stop_bot
from task.threeday import three_day
from task.db_backup import scheduler
from task.unban import premium_unban_watcher

dp = Dispatcher()
dp.message.middleware.register(BanUserMiddleware())
dp.message.middleware.register(AntiFloodMiddleware())
dp.include_router(handlers.router)


async def startup_answer(bot: Bot):
    await bot.send_message(652840346,"Bot ishga tushdi✅")
    asyncio.create_task(premium_unban_watcher(bot))
    asyncio.create_task(three_day(bot))
    asyncio.create_task(scheduler(bot))
    #asyncio.create_task(sleep_stop_bot(bot))
    asyncio.create_task(monthly_admin_notify(bot))

async def shutdown_answer(bot: Bot):
    await bot.send_message(652840346,"Bot to'xtadi❌")

async def start():
    await create_tables()
    await check_db_connection()
    dp.startup.register(startup_answer)
    dp.shutdown.register(shutdown_answer)



    bot = Bot(TOKEN)
    await dp.start_polling(bot)



asyncio.run(start())
