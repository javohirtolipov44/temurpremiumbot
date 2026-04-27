from datetime import datetime

import pytz
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatJoinRequest, Message, CallbackQuery

from config import INFO_URL, ADMINS, PREMIUM_URL, PREMIUM_ID
from crud.bot_sleep import get_bot_sleep
from crud.premium_users import get_one_premium_user
from crud.users import get_or_create_user, update_user_file_id
from database import async_session
from keyboard.karta_number import karta_kb
from keyboard.media import media_keyboard
from keyboard.message import message_kb
from keyboard.tolov import tolov_kb
from states.admin_state import AdminState
from states.send_user_messaage import SendUserMessageState

router = Router()
tz = pytz.timezone("Asia/Tashkent")

@router.chat_join_request()
async def join_request_handler(request: ChatJoinRequest, bot: Bot):
    user_id = request.from_user.id
    full_name = request.from_user.full_name
    username = f"@{request.from_user.username}" if request.from_user.username else "Mavjud emas"

    async with async_session() as session:
        await get_or_create_user(session, user_id, full_name, username)
        prem_user = await get_one_premium_user(session, user_id)

    if prem_user:
        await bot.approve_chat_join_request(
            chat_id=PREMIUM_ID,
            user_id=prem_user.chat_id,
        )

    await request.bot.send_message(user_id, text = f'Siz "{request.chat.title}" kanaliga qo‘shilish so‘rovini yubordingiz!\n'
        f"To'liq ma'lumot olish uchun /start tugmasini bosing!\n"
        )

@router.message(F.text.startswith("/start"))
async def start_handler(message: Message):
    async with async_session() as session:
        chat_id = message.chat.id
        full_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        await get_or_create_user(session, chat_id, full_name, username)
    await message.answer(f"<b>🔴 Diqqat! Tolov qilishdan avval ushbu postni yaxshilab oqib chiqing!\n\n🔴 Bank kartalari:\n\nBank nomi: Hamkor Bank \n\nKarta: 9860160134414384 \n\nQabul qiluvchi: Qurbonov Temurbek\n\nTelefon raqam: +998886135606\n\n1. Pasdagi silkaga bosing  https://t.me/+YHjKM-ZTgZhlMzli\nShu kanalga qoshilish sorovini Yuboring\n2.✅ TO'LOV QILISH ✅ ni bosib\nChekni tashlaysz ! Bo'ldi\n\n📌 Obuna tariflari:\n💎 1 oylik - 25 ming so'm\n💎 2 oylik - 50 ming so'm\n💎 3-oylik - 75-ming so'm\n💎 6-oylik- 150-ming so'm\n💎 12-oylik 300-ming so'm\n\n🔴 Bot sizga avtomatik ravishda xizmat korsatadi! Admin faqat chekni haqiyqiy yoki yoqligini tekshiradi xalos! Agar biror bir muammo yoki tushunmagan joyingiz bolsa {INFO_URL} kanalida qollanma bor!</b>",
                         disable_web_page_preview=True,
                         reply_markup=tolov_kb,
                         parse_mode="HTML")

@router.callback_query(F.data == "tolov")
async def tolov_handler(call: CallbackQuery):
    await call.message.edit_text(f"<b>Chekda aniq sana va vaqt, summa hamda o'tkazilgan karta raqam bo'lishi kerak!\n"
                                 f"Ps: bittadan ortiq rasm jo'natishga to'g'ri kelsa, donalab yuboring! Guruhlab yuborsangiz bot javob qaytarmaydi!</b>",
                    disable_web_page_preview=True,
                    reply_markup=karta_kb,
                    parse_mode="HTML")


def get_file_id(message: Message) -> str:
    if message.photo:
        return message.photo[-1].file_id
    if message.document:
        return message.document.file_id
    return ""


@router.message(SendUserMessageState.send_user_message)
async def send_user_message_handler(message: Message, state: FSMContext):
    if not message.from_user.id in ADMINS:
        await message.answer("Siz admin emassiz")
        return
    data = await state.get_data()
    chat_id = int(data["chat_id"])
    try:
        await message.copy_to(chat_id)
        await message.answer(f"<b>Xabaringiz muvaffaqiyatli yuborildi!!!</b>",parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b>{e}</b>",parse_mode="HTML")
    await state.clear()


@router.message(AdminState.send_message)
async def send_message_finish(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.update_data(
    from_chat_id=message.chat.id,
    message_id=message.message_id
)
    await message.answer("Xabar tasdiqlandi yuboraymi?", reply_markup=message_kb)


@router.message(F.photo | F.document)
async def handle_any_media(message: Message):
    file_id = get_file_id(message)
    chat_id = message.from_user.id
    async with async_session() as session:
        bot_sleep = await get_bot_sleep(session)
        chat_id = message.chat.id
        full_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        await get_or_create_user(session, chat_id, full_name, username)
        await update_user_file_id(session, chat_id, file_id)
        prem_user = await get_one_premium_user(session, chat_id)
    if prem_user:
        for ADMIN in ADMINS:
            await message.copy_to(chat_id=ADMIN,
                                  reply_markup=media_keyboard(chat_id),
                                  caption=f"<b>ID : <code>{chat_id}</code>\n\n"
                                          f"Obuna muddatini uzaytirish uchun</b>",
                                  parse_mode="HTML")
    else:
        for ADMIN in ADMINS:
            await message.copy_to(chat_id=ADMIN,
                                  reply_markup=media_keyboard(chat_id),
                                  caption=f"<b>ID : <code>{chat_id}</code>\n\n"
                                          f"Yangi obuna olish uchun</b>",
                                  parse_mode="HTML")

    if bot_sleep:
        sleep_time = datetime.fromtimestamp(bot_sleep.sleep_time, tz).strftime("%H:%M")
        await message.answer(f"🔴 Bot hozir offline holatda!\n\n"
                             f"🕐 {sleep_time} da online holatga qaytadi va o'sha paytda Premium kanalga qo'shilasiz!\n\n"
                             f"Tushunmovchiliklarni oldini olish maqsadida Premium Kanalga so'rov yuborganingizni yana bir bor tekshirib ko'rishingizni so'raymiz!\n\n"
                             f"{PREMIUM_URL}", disable_web_page_preview=True)
    else:
        await message.answer(f"Tez orada so'rovingizga javob beramiz!\n\n"
                         f"Tushunmovchiliklarni oldini olish maqsadida Premium Kanalga so'rov yuborganingizni yana bir bor tekshirib ko'rishingizni so'raymiz!\n\n"
                         f"{PREMIUM_URL}", disable_web_page_preview=True)

