import asyncio
import re
import gzip
import io
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

# Вставьте токен вашего бота (полученный у @BotFather)
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    # Получаем ID бизнес-подключения, чтобы отвечать от вашего имени
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        return

    # Парсим команду: /of t.me/nft/DurovsCap-1234 500
    parts = message.text.split()
    if len(parts) < 3:
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Формат: `/of <ссылка_на_NFT> <сумма>`",
            business_connection_id=business_connection_id
        )
        return

    link = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сумма должна быть числом.",
            business_connection_id=business_connection_id
        )
        return

    # Извлекаем слаг подарка (например, DurovsCap-1234)
    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Неверная ссылка на NFT-подарок.",
            business_connection_id=business_connection_id
        )
        return
    
    gift_slug = match.group(1)

    try:
        # 1. Удаляем исходное сообщение с командой от имени пользователя
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        # 2. Получаем анимацию подарка с Fragment
        animation_url = f"https://nft.fragment.com/gift/{gift_slug}.lottie.json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(animation_url) as resp:
                if resp.status == 200:
                    lottie_bytes = await resp.read()
                    
                    # 3. Конвертируем Lottie JSON в .tgs (GZIP)
                    tgs_bytes = gzip.compress(lottie_bytes)
                    
                    # 4. Отправляем анимированный стикер от имени пользователя
                    sticker_file = BufferedInputFile(tgs_bytes, filename=f"{gift_slug}.tgs")
                    await bot.send_sticker(
                        chat_id=message.chat.id,
                        sticker=sticker_file,
                        business_connection_id=business_connection_id
                    )

        # 5. Отправляем визуальный текст оффера с кнопками
        # Извлекаем имя из слага (например, DurovsCap-1234 -> Durov's Cap #1234)
        collection_name = gift_slug.split('-')[0]
        # Простая визуализация, можно улучшить
        display_name = f"{collection_name} #{gift_slug.split('-')[-1]}" 

        offer_text = (
            f"Пользователь (@{message.from_user.username}) "
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
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"❌ Ошибка: {e}",
            business_connection_id=business_connection_id
        )

# Обработчик нажатий на кнопки (заглушка)
@dp.callback_query(F.data.startswith("fake_"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    await callback.answer("Это визуальная имитация оффера.", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
