import asyncio
import os
import re
import gzip
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

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
        # 1. Удаляем команду через встроенный метод сообщения
        await message.delete()

        # 2. Скачиваем и отправляем анимацию
        animation_url = f"https://nft.fragment.com/gift/{gift_slug}.lottie.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(animation_url) as resp:
                if resp.status == 200:
                    lottie_bytes = await resp.read()
                    tgs_bytes = gzip.compress(lottie_bytes)
                    sticker_file = BufferedInputFile(tgs_bytes, filename=f"{gift_slug}.tgs")
                    await bot.send_sticker(
                        chat_id=message.chat.id,
                        sticker=sticker_file,
                        business_connection_id=business_connection_id
                    )

        # 3. Формируем текст оффера
        collection_name = gift_slug.split('-')[0]
        display_name = f"{collection_name} #{gift_slug.split('-')[-1]}"
        
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        offer_text = (
            f"Пользователь {username} "
            f"предлагает вам\n"
            f"**{amount} ⭐** за подарок **{display_name}**."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Отклонить", callback_data="fake_decline"),
                InlineKeyboardButton(text="Принять", callback_data="fake_accept")
            ]
        ])

        await bot.send_message(
            chat_id=message.chat.id,
            text=offer_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id
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
