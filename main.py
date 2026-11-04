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
    # Отладочный вывод: покажет в логах, что бот увидел команду
    print(f"==================================================")
    print(f"!!! ПОЛУЧЕНА КОМАНДА: {message.text} !!!")
    print(f"==================================================")

    business_connection_id = message.business_connection_id
    if not business_connection_id:
        print("!!! ОШИБКА: НЕТ business_connection_id !!!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        print("!!! ОШИБКА: НЕВЕРНЫЙ ФОРМАТ КОМАНДЫ !!!")
        return

    link = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        print("!!! ОШИБКА: СУММА НЕ ЯВЛЯЕТСЯ ЧИСЛОМ !!!")
        return

    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        print("!!! ОШИБКА: НЕВЕРНАЯ ССЫЛКА !!!")
        return
    
    gift_slug = match.group(1)

    try:
        # 1. Удаляем команду
        print(f"Удаляем сообщение {message.message_id}...")
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        # 2. Готовим картинку подарка
        photo_url = f"https://nft.fragment.com/gift/{gift_slug}.webp"
        
        # Форматируем имя для красоты (DurovsCap-1234 -> Durov's Cap #1234)
        raw_name = gift_slug.split('-')[0]
        pretty_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name) 
        display_name = f"{pretty_name} #{gift_slug.split('-')[-1]}"
        
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        # Текст, как на реальном оффере
        caption_text = (
            f"<b>Telegram</b>\n"
            f"<b>{display_name}</b>\n\n"
            f"Пользователь {username}\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <b>{pretty_name}</b>."
        )

        # Кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать подарок", url=link)],
            [
                InlineKeyboardButton(text="Отклонить", callback_data="fake_decline"),
                InlineKeyboardButton(text="Принять", callback_data="fake_accept")
            ]
        ])

        # 3. Отправляем визуальный оффер (Фото + Текст + Кнопки)
        print("Отправляем фото с оффером...")
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_url,
            caption=caption_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )

        # 4. Отправляем анимацию стикером следом (если нужно)
        try:
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
                        print("Стикер отправлен.")
        except Exception as sticker_error:
            print(f"Не удалось отправить стикер: {sticker_error}")

        print("ОФФЕР УСПЕШНО ОТПРАВЛЕН!")

    except Exception as e:
        print(f"!!! ОШИБКА ПРИ ОТПРАВКЕ: {e} !!!")
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"❌ <b>Ошибка:</b> {e}",
                business_connection_id=business_connection_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

@dp.callback_query(F.data.startswith("fake_"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    await callback.answer("Это визуальная имитация оффера.", show_alert=True)

async def main():
    print("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
