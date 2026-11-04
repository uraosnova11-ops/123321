import asyncio
import os
import re
import gzip
import io
import random
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
    try:
        amount = int(parts[2])
    except ValueError:
        return await message.edit_text("❌ Сумма должна быть числом.")

    # Извлекаем слаг подарка (например, DurovsCap-1234)
    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        return await message.edit_text("❌ Неверная ссылка на NFT-подарок.")
    
    gift_slug = match.group(1)

    try:
        # 1. Мгновенно удаляем команду из чата (чтобы никто не видел)
        await message.delete()

        # 2. Получаем Lottie-анимацию подарка с Fragment
        animation_url = None
        owner_id = None
        
        async with aiohttp.ClientSession() as session:
            # Запрос к Fragment за информацией о подарке
            async with session.get(f"https://fragment.com/api/gift/{gift_slug}") as resp:
                if resp.status == 200:
                    gift_data = await resp.json()
                    animation_url = gift_data.get("animation_url") or gift_data.get("model", {}).get("animation_url")
                    # Пытаемся получить ID владельца (если он есть в ответе)
                    owner_id = gift_data.get("owner", {}).get("id") 

        # 3. Отправляем визуальный оффер (стикер)
        if animation_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(animation_url) as resp:
                    lottie_bytes = await resp.read()
            
            # Конвертируем в Telegram Sticker (.tgs)
            tgs_bytes = gzip.compress(lottie_bytes)
            
            # Отправляем .tgs прямо в чат
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker=io.BytesIO(tgs_bytes),
                reply_to_message_id=message.reply_to_message_id
            )

        # 4. Отправляем оффер через MTProto
        # Генерируем случайный ID для защиты от дублей
        random_id = random.randint(-2**63, 2**63 - 1)
        
        # ВНИМАНИЕ: Если owner_id не найден, отправляем оффер в текущий чат (для теста).
        # В реальной работе тут должен быть ID владельца подарка.
        target_peer = owner_id if owner_id else message.chat.id

        await client.invoke(
            SendStarGiftOffer(
                peer=target_peer,
                slug=gift_slug,
                price=StarsAmount(amount=amount * 10**9), # Перевод в нано-звезды
                duration=86400, # 24 часа
                random_id=random_id,
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
        # В случае ошибки пишем в чат, чтобы вы знали
        try:
            await client.send_message(chat_id=message.chat.id, text=f"❌ Ошибка: {e}")
        except Exception:
            pass

if __name__ == "__main__":
    print("Бот запущен...")
    app.run()
