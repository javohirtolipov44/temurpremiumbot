import asyncio
from aiogram import Bot

from config import PREMIUM_ID, ADMINS, PREMIUM_URL
from crud.premium_users import get_expired_users, delete_premium_user
from database import async_session
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

async def is_user_in_chat(bot, chanel_id, chat_id) -> bool:
    try:
        member = await bot.get_chat_member(chanel_id, chat_id)
        return member.status not in ("left", "kicked")
    except TelegramBadRequest:
        return False
    except TelegramForbiddenError:
        return False



async def premium_unban_watcher(bot: Bot):
    while True:
        try:
            async with async_session() as session:
                expired_users = await get_expired_users(session)

            for prem_user in expired_users:
                chat_id = prem_user.chat_id

                try:
                    await bot.unban_chat_member(PREMIUM_ID, chat_id)
                    await bot.send_message(chat_id, "Obuna muddatingiz tugadi.\n\n"
                                                        f"{PREMIUM_URL}")
                    for ADMIN in ADMINS:
                        await bot.send_message(ADMIN, "Obuna muddati tugadi\n"
                                                          f"ID : {chat_id}")
                except Exception as e:
                    for ADMIN in ADMINS:
                        await bot.send_message(ADMIN,f"{e}\n\n"
                                                         f"ID : {chat_id}\n"
                                                         f"unban.py")
                in_chat = await is_user_in_chat(bot, PREMIUM_ID, chat_id)
                if not in_chat:
                    await delete_premium_user(session, chat_id)      

        except Exception as e:
            for ADMIN in ADMINS:
                await bot.send_message(ADMIN, f"{e}")

        await asyncio.sleep(300)  # ⏱ 5 minut
