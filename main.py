import asyncio
import os
import re
import gzip
import io
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message

# Данные берутся из переменных окружения (Secrets в GitHub)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

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
        # 1. Мгновенно удаляем команду из чата
        await message.delete()

        # 2. Пытаемся скачать и отправить анимацию (если получится)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://fragment.com/api/gift/{gift_slug}") as resp:
                    if resp.status == 200:
                        gift_data = await resp.json()
                        animation_url = gift_data.get("animation_url") or gift_data.get("model", {}).get("animation_url")
                        if animation_url:
                            async with session.get(animation_url) as anim_resp:
                                lottie_bytes = await anim_resp.read()
                            tgs_bytes = gzip.compress(lottie_bytes)
                            await client.send_sticker(
                                chat_id=message.chat.id,
                                sticker=io.BytesIO(tgs_bytes),
                                reply_to_message_id=message.reply_to_message_id
                            )
        except Exception:
            pass # Если анимация не скачалась, просто идём дальше

        # 3. ОТПРАВКА ОФФЕРА (используем встроенный метод Pyrofork)
        # ВНИМАНИЕ: Для теста отправляем оффер в текущий чат (в "Избранное").
        # В реальной работе здесь должен быть owner_id владельца подарка.
        await client.send_gift_purchase_offer(
            owner_id=message.chat.id,  # Кому отправляем (сейчас - текущий чат)
            gift_name=gift_slug,       # Слаг подарка
            price=amount,              # Сумма в звездах
            duration=86400             # 24 часа
        )

        # 4. Подтверждение в чат
        status_msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ Оффер на **{amount} ⭐** за подарок `{gift_slug}` отправлен!"
        )
        await asyncio.sleep(10)
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка: {e}")
        try:
            await client.send_message(chat_id=message.chat.id, text=f"❌ Ошибка: {e}")
        except Exception:
            pass

if __name__ == "__main__":
    print("Бот запущен...")
    app.run()
