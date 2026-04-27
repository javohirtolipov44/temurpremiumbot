from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboard.callback_data.media import MediaCallback


def media_keyboard(chat_id: int):
    media_kb = InlineKeyboardBuilder()

    for month in (1, 2, 3, 6, 12):
        media_kb.button(
            text=f"{month}-oy",
            callback_data=MediaCallback(
                chat_id=chat_id,
                months=month,
            ).pack()
        )
    media_kb.button(text="✉️ Xabar yuborish", callback_data=f"sendmes:{chat_id}")
    media_kb.button(text="❌ Bekor qilish", callback_data=f"media_cancel:{chat_id}")

    media_kb.adjust(1)
    return media_kb.as_markup()
