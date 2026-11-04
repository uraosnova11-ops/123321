import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

    try:
        # 1. Мгновенно удаляем команду
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        # 2. Форматируем текст
        raw_name = gift_slug.split('-')[0]
        pretty_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name) 
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        # 3. Текст сообщения
        # Ссылку вставляем прямо в текст. Telegram сам сделает её кликабельной.
        caption_text = (
            f"Пользователь ({username})\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a>."
        )

        # 4. Кнопки (только Отклонить и Принять)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Отклонить", callback_data="fake_decline"),
                InlineKeyboardButton(text="Принять", callback_data="fake_accept")
            ]
        ])

        # 5. Отправляем сообщение с нативным превью НАД текстом
        await bot.send_message(
            chat_id=message.chat.id,
            text=caption_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                url=link,                 # Ссылка, для которой генерируем превью
                show_above_text=True,     # Карточка будет НАД текстом
                prefer_large_media=True   # Крупный размер превью
            )
        )

    except Exception as e:
        print(f"Ошибка: {e}")

@dp.callback_query(F.data.startswith("fake_"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    await callback.answer("Это визуальная имитация оффера.", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
