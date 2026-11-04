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

    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match:
        return await message.edit_text("❌ Неверная ссылка на NFT-подарок.")
    
    gift_slug = match.group(1)

    try:
        # Удаляем команду
        await message.delete()

        # Пытаемся отправить анимацию (не критично, если не получится)
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
                                sticker=io.BytesIO(tgs_bytes)
                            )
        except Exception:
            pass

        # ОТПРАВКА ОФФЕРА (Используем raw API)
        random_id = random.randint(-2**63, 2**63 - 1)
        
        # ВНИМАНИЕ: Метод SendStarGiftOffer не требует указания peer (получателя).
        # Он автоматически отправляется текущему владельцу подарка по его slug.
        await client.invoke(
            SendStarGiftOffer(
                slug=gift_slug,
                price=StarsAmount(amount=amount),
                duration=86400, # 24 часа
                random_id=random_id
            )
        )

        status_msg = await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ Оффер на **{amount} ⭐** за подарок `{gift_slug}` успешно отправлен владельцу!"
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
