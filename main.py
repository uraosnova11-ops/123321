import asyncio
import os
import re
import gzip
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.raw.functions.payments import SendStarGiftOffer
from pyrogram.raw.types import StarsAmount

# Данные берутся из переменных окружения (Secrets в GitHub)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# Инициализация User-bot
app = Client(
    "offer_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

@app.on_message(filters.regex(r"^/of\s+") & filters.me)
async def handle_offer_command(client: Client, message: Message):
    text = message.text or message.caption
    if not text:
        return

    # Парсинг: /of t.me/nft/DurovsCap-1234 500
    parts = text.split()
    if len(parts) < 3:
        return await message.edit_text("❌ Формат: `/of <ссылка> <сумма>`")
    
    link = parts[1]
    amount = int(parts[2])

    # Извлекаем слаг подарка (например, DurovsCap-1234)
    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        return await message.edit_text("❌ Неверная ссылка на NFT-подарок.")
    
    gift_slug = match.group(1)

    try:
        # 1. Мгновенно удаляем команду из чата (чтобы никто не видел)
        await message.delete()

        # 2. Получаем Lottie-анимацию подарка с Fragment
        # Используем публичный эндпоинт фрагмента для получения метаданных
        async with aiohttp.ClientSession() as session:
            # Запрос к Fragment за информацией о подарке
            async with session.get(f"https://fragment.com/api/gift/{gift_slug}") as resp:
                if resp.status == 200:
                    gift_data = await resp.json()
                    animation_url = gift_data.get("animation_url") or gift_data.get("model", {}).get("animation_url")
                else:
                    animation_url = None

        # 3. Отправляем визуальный оффер и сам запрос в чат
        if animation_url:
            # Скачиваем анимацию
            async with aiohttp.ClientSession() as session:
                async with session.get(animation_url) as resp:
                    lottie_bytes = await resp.read()
            
            # Конвертируем в Telegram Sticker (.tgs)
            tgs_bytes = gzip.compress(lottie_bytes)
            
            # Отправляем .tgs прямо в чат (визуальная часть)
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker=tgs_bytes,
                reply_to_message_id=message.reply_to_message_id
            )

        # 4. Отправляем оффер через MTProto
        # Получаем информацию о владельце подарка (упрощенно через slug)
        # В реальности нужно запросить peer владельца, если оффер отправляется в ЛС
        # Здесь отправляем оффер от вашего аккаунта
        await client.invoke(
            SendStarGiftOffer(
                slug=gift_slug,
                price=StarsAmount(amount=amount * 10**9),  # Перевод в нано-звезды
                duration=86400, # 24 часа
                allow_paid_stars=0
            )
        )

        # Подтверждение в чат
        status_msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ Оффер на **{amount} ⭐** за подарок `{gift_slug}` успешно отправлен!"
        )
        await asyncio.sleep(10)
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка: {e}")
        # В случае ошибки возвращаем сообщение, чтобы вы знали
        await client.send_message(chat_id=message.chat.id, text=f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("Бот запущен...")
    app.run()
