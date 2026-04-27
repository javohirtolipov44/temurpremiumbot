import asyncio

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import time
import pytz

from config import PREMIUM_URL, PREMIUM_ID, ADMINS
from crud.ban_users import create_or_update_ban_user, get_one_ban_user, delete_ban_user
from crud.bot_sleep import create_or_update, delete_bot_sleep
from crud.premium_users import get_or_create_or_extend_premium_user, get_one_premium_user, end_update_premium_user, start_update_premium_user, delete_premium_user, all_premium_users
from crud.users import get_user_by_chat_id, get_all_users
from database import async_session
from keyboard.admin import admin_kb
from keyboard.callback_data.media import MediaCallback
from keyboard.prem_users_info import prem_user_caption
from keyboard.tolov import obuna_kb
from states.admin_state import AdminState
from states.prem_users_state import PremiumUserUpdate
from states.send_user_messaage import SendUserMessageState
from task.unban import is_user_in_chat

router = Router()
tz = pytz.timezone("Asia/Tashkent")


@router.message(F.text.startswith("/admin"))
async def admin(message: Message):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    await message.answer("Admin panelga xush kelibsiz!!!", reply_markup=admin_kb)


@router.callback_query(F.data == "statistika")
async def statistika(callback: CallbackQuery):
    if not callback.from_user.id in ADMINS:
        await callback.answer("Siz admin emassiz")
        return
    async with async_session() as session:
        prem_user = await all_premium_users(session)
        user = await get_all_users(session)
    try:
        await callback.message.edit_text(f"Barcha premium obunachilar: {len(prem_user)}\n\n"
                                     f"Barcha bot obunachilari: {len(user)}",
                                     reply_markup=admin_kb)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "send_message")
async def send_message(callback: CallbackQuery, state: FSMContext):
    if not callback.from_user.id in ADMINS:
        await callback.answer("Siz admin emassiz")
        return
    await state.set_state(AdminState.send_message)
    await callback.message.edit_text("Xabaringizni yuboring")


@router.callback_query(F.data == "send")
async def confirm_broadcast(call: CallbackQuery, state: FSMContext, bot: Bot):
    if call.from_user.id not in ADMINS:
        return

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    async with async_session() as session:
        users = await get_all_users(session)  # PostgreSQL async

    await call.message.edit_text(
        f"⏳ Xabar yuborilmoqda...\n"
        f"👥 Foydalanuvchilar: {len(users)}"
    )

    # 🔥 ASOSIY JOY
    asyncio.create_task(
        broadcast_copy(bot, from_chat_id, message_id, users)
    )
    await call.answer("🚀 Broadcast boshlandi")
    await state.clear()

async def broadcast_copy(bot: Bot, from_chat, msg_id, users):
    start_time = time.monotonic()   # ⏱ boshlanish vaqti
    success = 0
    failed = 0

    total = len(users)

    for user in users:
        try:
            await bot.copy_message(user.chat_id, from_chat, msg_id)
            success += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(user.chat_id, from_chat, msg_id)
                success += 1
            except:
                failed += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception as e:
            failed += 1
            print(f"Xato {user.chat_id}: {e}")

        await asyncio.sleep(0.05)  # ⚡ tez, xavfsiz

    # ⏱ tugash vaqti
    elapsed = time.monotonic() - start_time

    minutes, seconds = divmod(int(elapsed), 60)

    report = (
        "✅ Broadcast yakunlandi\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"📬 Yuborildi: {success}\n"
        f"❌ Xatolik: {failed}\n"
        f"⏱ Sarflangan vaqt: {minutes} daqiqa {seconds} soniya"
    )

    # 📣 Admin(lar)ga xabar berish
    await bot.send_message(from_chat, report)

@router.callback_query(MediaCallback.filter())
async def handle_media_callback(call: CallbackQuery, callback_data: MediaCallback):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = callback_data.chat_id
    months = callback_data.months
    await call.answer()
    try:
        async with async_session() as session:
            user = await get_user_by_chat_id(session, chat_id)
            if user:
                username = user.username
                full_name = user.full_name
            file_id = user.file_id if user else None

        await call.bot.approve_chat_join_request(
            chat_id=PREMIUM_ID,
            user_id=chat_id
        )

        async with async_session() as session:
            prem_user = await get_or_create_or_extend_premium_user(session, chat_id, months, file_id)
            start_at_dt = datetime.fromtimestamp(prem_user.start_at, tz)
            end_at_dt = datetime.fromtimestamp(prem_user.end_at, tz)
            start_at = start_at_dt.strftime("%d.%m.%Y %H:%M")
            end_at = end_at_dt.strftime("%d.%m.%Y %H:%M")



        await call.message.reply(f"📄 <b>Obuna ma'lumotlari\n\n"
                                 f"🆔 ID: <code>{chat_id}</code>\n"
                                 f"🚹 FulName: <code>{full_name}</code>\n"
                                 f"🔄 UserName: <code>{username}</code>\n"
                                 f"⏱ Boshlanish: {start_at}\n"
                                 f"⏳ Tugash: {end_at}</b>",
                                 parse_mode="HTML")

        await call.bot.send_message(ADMINS[0], f"📄 <b>Obuna ma'lumotlari\n\n"
                                 f"🆔 ID: <code>{chat_id}</code>\n"
                                 f"🚹 FulName: <code>{full_name}</code>\n"
                                 f"🔄 UserName: <code>{username}</code>\n"
                                 f"⏱ Boshlanish: {start_at}\n"
                                 f"⏳ Tugash: {end_at}</b>",
                                 parse_mode="HTML")

        await call.bot.send_message(chat_id, f"📄 <b>Obuna ma'lumotlari\n\n"
                                            f"⏱ Boshlanish: {start_at}\n"
                                            f"⏳ Tugash: {end_at}\n\n"
                                            f"{PREMIUM_URL}</b>",
                                            parse_mode="HTML")

        await call.bot.send_message(chat_id, f"📄 <b>Obunangizni uzaytirmoqchi bo'lsangiz, shunchaki to'lov qilib chekni shu yerga yuboring!</b>",
                                    parse_mode="HTML",
                                    reply_markup=obuna_kb)


    except TelegramBadRequest as e:

        if "HIDE_REQUESTER_MISSING" in e.message:
            await call.message.reply("<b>Kanalga qo'shilish so'rovini yubormagan</b>",
                                     parse_mode="HTML")
            await call.bot.send_message(chat_id,"<b>Iltimos kanalga qo'shilish so'rovini yuboring!\n\n"
                                        f"{PREMIUM_URL}</b>",
                                        disable_web_page_preview=True,
                                        parse_mode="HTML")
        elif "USER_ALREADY_PARTICIPANT" in e.message:
            async with async_session() as session:
                prem_user = await get_or_create_or_extend_premium_user(session, chat_id, months, file_id)
                start_at_dt = datetime.fromtimestamp(prem_user.start_at, tz)
                end_at_dt = datetime.fromtimestamp(prem_user.end_at, tz)
                start_at = start_at_dt.strftime("%d.%m.%Y %H:%M")
                end_at = end_at_dt.strftime("%d.%m.%Y %H:%M")

            await call.message.reply(f"📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                                     f"🆔 ID: <code>{chat_id}</code>\n"
                                     f"🚹 FulName: <code>{full_name}</code>\n"
                                     f"🔄 UserName: <code>{username}</code>\n"
                                     f"⏱ Boshlanish: {start_at}\n"
                                     f"⏳ Tugash: {end_at}</b>",
                                     parse_mode="HTML")

            await call.bot.send_message(ADMINS[0], f"📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                                 f"🆔 ID: <code>{chat_id}</code>\n"
                                 f"🚹 FulName: <code>{full_name}</code>\n"
                                 f"🔄 UserName: <code>{username}</code>\n"
                                 f"⏱ Boshlanish: {start_at}\n"
                                 f"⏳ Tugash: {end_at}</b>",
                                 parse_mode="HTML")


            await call.bot.send_message(chat_id, f"📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                                                 f"⏱ Boshlanish: {start_at}\n"
                                                 f"⏳ Tugash: {end_at}\n\n"
                                                 f"{PREMIUM_URL}</b>",
                                        parse_mode="HTML")
            await call.bot.send_message(chat_id,
                                        f"📄 <b>Obunangizni uzaytirmoqchi bo'lsangiz, shunchaki to'lov qilib chekni shu yerga yuboring!</b>",
                                        parse_mode="HTML",
                                        reply_markup=obuna_kb)
        elif "USER_CHANNELS_TOO_MUCH" in e.message:
            await call.message.reply("<b>Foydalanuvchi kanallari ko'pligi sababli qo'shilmadi</b>",
                                     parse_mode="HTML")
            await call.bot.send_message(chat_id,"<b>Sizda kanallar soni ko'pligi sababli premiumga qo'shila olmaysiz\nBirorta kanalni o'chirib qayta chek yuborin\n\n"
                                        f"{PREMIUM_URL}</b>",
                                        disable_web_page_preview=True,
                                        parse_mode="HTML")
        else:
            await call.message.reply(f"{e}")

    except Exception as e:
        await call.message.reply(f"🆔 ID: <code>{chat_id}</code>\n\n"
                                 f"{e}")


@router.callback_query(F.data.startswith("media_cancel"))
async def media_cancel_handler(call: CallbackQuery):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = int(call.data.split(":")[1])
    await call.answer()
    await call.message.reply(
        f"⛔ Foydalanuvchi ({chat_id}) cheki rad etildi"
    )
    await call.bot.send_message(chat_id, "Siz yuborgan chek rad etildi.\n"
                      "Iltimos soxta chek yubormang aks holda ban qilinasiz va botdan foydalana olmaysiz")


@router.callback_query(F.data.startswith("sendmes"))
async def sendme_handler(call: CallbackQuery, state: FSMContext):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = int(call.data.split(":")[1])
    await call.answer()
    await call.message.reply("<b>Xabaringizni yozing!</b>",
                             parse_mode="HTML")
    await state.set_state(SendUserMessageState.send_user_message)
    await state.update_data(chat_id=chat_id)

@router.message(F.text.startswith("/allpremiumusersremovetochanel"))
async def all_premium_users_remove_to_chanel_handler(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    
    async with async_session() as session:
        prem_users = await all_premium_users(session)
    try:
        for prem_user in prem_users:
            chat_id = prem_user.chat_id
    
            await message.bot.unban_chat_member(PREMIUM_ID, chat_id)
                            
            for ADMIN in ADMINS:
                await message.bot.send_message(ADMIN, f"ID : {chat_id}\n"
                                                               f"Kanaldan chiqarildi")
    except Exception as e:
            for ADMIN in ADMINS:
                await message.bot.send_message(ADMIN,f"{e}\n\n"
                                                         f"ID : {chat_id}") 


@router.message(F.text.startswith("/allpremiumusersremovetochanel"))
async def all_premium_users_remove_to_chanel_handler(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    
    async with async_session() as session:
        prem_users = await all_premium_users(session)
    
    for prem_user in prem_users:
        chat_id = prem_user.chat_id

        try:
            await message.bot.unban_chat_member(PREMIUM_ID, chat_id)
                        
            for ADMIN in ADMINS:
                await message.bot.send_message(ADMIN, f"ID : {chat_id}\n"
                                                           f"Kanaldan chiqarildi")
        except Exception as e:
            for ADMIN in ADMINS:
                await message.bot.send_message(ADMIN,f"{e}\n\n"
                                                         f"ID : {chat_id}\n\n{PREMIUM_ID}")   


@router.message(F.text.startswith("/sleep"))
async def sleep_bot_handler(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Siz admin emassiz")
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("Foydalanish: /sleep <soat>")
        return
    if parts[1] == "stop":
        async with async_session() as session:
            await delete_bot_sleep(session)
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, "Bot yana faol ishlamoqda")
    else:
        try:
            hours = int(parts[1])
            async with async_session() as session:
                await create_or_update(session,hours)
        except ValueError:
            await message.answer("Faqat son kiriting. Masalan: /sleep 9\n"
                                 "Yoki /sleep stop")
            return
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, f"Bot {hours} soat uxlaydi 😴\n"
                         f"Siz bugun juda yaxshi ishladingiz 😁\n"
                         f"Xayrli tun yaxshi dam oling")


@router.callback_query(F.data.startswith("started"))
async def started_handler(call: CallbackQuery, state: FSMContext):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = int(call.data.split(":")[1])
    await call.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    await call.message.answer(f"<b>Iltimos sanani kiriting\n"
                              f"Masalan:\n\n"
                              f"{datetime.now(tz).strftime('%Y-%m-%d %H:%M')}</b>",
                              parse_mode="HTML")
    await state.set_state(PremiumUserUpdate.start_update)
    await state.update_data(chat_id=chat_id)


@router.message(PremiumUserUpdate.start_update)
async def start_update_handler(message: Message, state: FSMContext):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    data = await state.get_data()
    chat_id = int(data["chat_id"])
    async with async_session() as session:
        prem_user = await start_update_premium_user(session, chat_id, message.text)
    start_at_dt = datetime.fromtimestamp(prem_user.start_at, tz)
    end_at_dt = datetime.fromtimestamp(prem_user.end_at, tz)
    start_at = start_at_dt.strftime("%d.%m.%Y %H:%M")
    end_at = end_at_dt.strftime("%d.%m.%Y %H:%M")
    await message.answer_photo(
        photo=prem_user.file_id,
        caption="📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                f"🆔 ID: <code>{chat_id}</code>\n"
                f"⏱ Boshlanish: {start_at}\n"
                f"⏳ Tugash: {end_at}</b>",
        parse_mode="HTML",
        reply_markup=prem_user_caption(chat_id))

    await message.bot.send_message(chat_id=chat_id,
                         text="📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                                 f"⏱ Boshlanish: {start_at}\n"
                                 f"⏳ Tugash: {end_at}</b>",
                         parse_mode="HTML"
                         )
    await state.clear()


@router.callback_query(F.data.startswith("ended"))
async def ended_handler(call: CallbackQuery, state: FSMContext):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = int(call.data.split(":")[1])
    await call.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    await call.message.answer(f"<b>Iltimos sanani kiriting\n"
                              f"Masalan:\n\n"
                              f"{datetime.now(tz).strftime('%Y-%m-%d %H:%M')}</b>",
                              parse_mode="HTML")
    await state.set_state(PremiumUserUpdate.end_update)
    await state.update_data(chat_id=chat_id)


@router.message(PremiumUserUpdate.end_update)
async def end_update_handler(message: Message, state: FSMContext):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    data = await state.get_data()
    chat_id = int(data["chat_id"])
    async with async_session() as session:
        prem_user = await end_update_premium_user(session, chat_id, message.text)
    start_at_dt = datetime.fromtimestamp(prem_user.start_at, tz)
    end_at_dt = datetime.fromtimestamp(prem_user.end_at, tz)
    start_at = start_at_dt.strftime("%d.%m.%Y %H:%M")
    end_at = end_at_dt.strftime("%d.%m.%Y %H:%M")
    await message.answer_photo(
        photo=prem_user.file_id,
        caption="📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                f"🆔 ID: <code>{chat_id}</code>\n"
                f"⏱ Boshlanish: {start_at}\n"
                f"⏳ Tugash: {end_at}</b>",
        parse_mode="HTML",
        reply_markup=prem_user_caption(chat_id))

    await message.bot.send_message(chat_id=chat_id,
                         text="📄 <b>Obuna ma'lumotlari o'zgardi\n\n"
                                 f"⏱ Boshlanish: {start_at}\n"
                                 f"⏳ Tugash: {end_at}</b>",
                         parse_mode="HTML"
                         )
    await state.clear()


@router.callback_query(F.data.startswith("deleted"))
async def deleted_handler(call: CallbackQuery, bot: Bot):
    if not call.from_user.id in ADMINS:
        await call.message.answer("Siz admin emassiz")
        return
    chat_id = int(call.data.split(":")[1])
    await call.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    async with async_session() as session:
        try:
            await bot.unban_chat_member(PREMIUM_ID, chat_id)
            await bot.send_message(chat_id, "Obuna muddatingiz tugadi.\n\n"
                                            f"{PREMIUM_URL}")
            for ADMIN in ADMINS:
                await bot.send_message(ADMIN, "Kanaldan o'chirildi\n"
                                              f"ID : {chat_id}")
        except Exception as e:
            for ADMIN in ADMINS:
                await bot.send_message(ADMIN, f"{e}\n\n"
                                              f"ID : {chat_id}\n"
                                              f"admin.py")
        in_chat = await is_user_in_chat(bot, PREMIUM_ID, chat_id)
        if not in_chat:
            await delete_premium_user(session, chat_id)
            for ADMIN in ADMINS:
                await bot.send_message(ADMIN, "Bazadan o'chirildi\n"
                                              f"ID : {chat_id}")


@router.message(F.text.startswith("/ban_info"))
async def ban_info(message: Message):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    chat_id = int(message.text.split(" ")[1])
    async with async_session() as session:
        ban_user = await get_one_ban_user(session, chat_id)
    ban_time_dt = datetime.fromtimestamp(ban_user.ban_time, tz)
    ban_time = ban_time_dt.strftime("%d.%m.%Y")
    await message.answer(f"ID : {chat_id}\n\n"
                        f"Ban muddati: {ban_time}")


@router.message(F.text.startswith("/ban_delete"))
async def delete_ban_users(message: Message):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    chat_id = int(message.text.split(" ")[1])
    try:
        async with async_session() as session:
            natija = await delete_ban_user(session, chat_id)
        if natija:
            await message.answer(f"<b>ID : {chat_id}\n\n"
                                 f"Ban olib tashlandi</b>",
                                 parse_mode="HTML")
            await message.bot.send_message(chat_id, "<b>Endi botdan foydalanishingiz mumkin.</b>",
                                   parse_mode="HTML")
        else:
            await message.answer(f"<b>ID : {chat_id}\n\n"
                                 f"Ban emas</b>",
                                 parse_mode="HTML")
    except Exception as e:
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, f"{e}\n\n"
                                          f"admin.py")


@router.message(F.text.startswith("/ban"))
async def ban(message: Message):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    _, data = message.text.split(" ", 1)
    chat_id_str, days_str = data.split(",")

    chat_id = int(chat_id_str.strip())
    ban_days = int(days_str.strip())
    async with async_session() as session:
        ban_user = await create_or_update_ban_user(session, chat_id, ban_days)
    ban_time_dt = datetime.fromtimestamp(ban_user.ban_time, tz)
    ban_time = ban_time_dt.strftime("%d.%m.%Y")
    try:
        await message.bot.send_message(chat_id, "<b>Endi botdan ko'rsatilgan vaqt kelmaguncha foydalana olmaysiz.\n\n"
                                        f"{ban_time}</b>",
                                       parse_mode="HTML")
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, f"ID : {chat_id}\n\n"
                                                  f"Ban muddati: {ban_time}")
    except Exception as e:
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, f"{e}\n\n"
                                          f"admin.py")



@router.message(F.text.startswith("/delete"))
async def delete_prem_users(message: Message, bot: Bot):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    chat_id = int(message.text.split(" ")[1])
    try:
        async with async_session() as session:
            await delete_premium_user(session, chat_id)
        for ADMIN in ADMINS:
            await bot.send_message(ADMIN, "Bazadan o'chirildi\n"
                                              f"ID : {chat_id}")
    except Exception as e:
        for ADMIN in ADMINS:
            await message.bot.send_message(ADMIN, f"{e}\n\n"
                                          f"admin.py")








@router.message(F.text)
async def id_info(message: Message):
    if message.from_user.id in ADMINS:
        if message.text.isdigit():
            try:
                chat_id = int(message.text)
                async with async_session() as session:
                    prem_user = await get_one_premium_user(session, chat_id)
                if not prem_user:
                    await message.answer("User premiumda mavjud emas")
                else:
                    start_at_dt = datetime.fromtimestamp(prem_user.start_at, tz)
                    end_at_dt = datetime.fromtimestamp(prem_user.end_at, tz)
                    start_at = start_at_dt.strftime("%d.%m.%Y %H:%M")
                    end_at = end_at_dt.strftime("%d.%m.%Y %H:%M")
                    try:
                        await message.answer_photo(
                            photo=prem_user.file_id,
                            caption="📄 <b>Obuna ma'lumotlari\n\n"
                                         f"🆔 ID: <code>{chat_id}</code>\n"
                                         f"⏱ Boshlanish: {start_at}\n"
                                         f"⏳ Tugash: {end_at}</b>",
                                         parse_mode="HTML",
                                         reply_markup=prem_user_caption(chat_id))
                    except TelegramBadRequest as e:
                        # Agar Photo bo‘lsa, Document qilib bo‘lmaydi
                        if "can't use file of type Document as Photo" in str(e):
                            await message.answer_document(
                            document=prem_user.file_id,
                            caption="📄 <b>Obuna ma'lumotlari\n\n"
                                         f"🆔 ID: <code>{chat_id}</code>\n"
                                         f"⏱ Boshlanish: {start_at}\n"
                                         f"⏳ Tugash: {end_at}</b>",
                                         parse_mode="HTML",
                                         reply_markup=prem_user_caption(chat_id))
            except Exception as e:
                for ADMIN in ADMINS:
                    await message.bot.send_message(ADMIN, f"{e}\n\n"
                                          f"admin.py")
