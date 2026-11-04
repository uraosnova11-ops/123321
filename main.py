import asyncio
import os
import re
import subprocess
import tempfile
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from rlottie_python import LottieAnimation

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def convert_lottie_to_mp4(lottie_bytes: bytes, output_path: str):
    """Конвертирует Lottie JSON в MP4 с помощью rlottie-python и ffmpeg."""
    # Загружаем анимацию из байтов
    anim = LottieAnimation.from_data(data=lottie_bytes.decode('utf-8'))
    total_frames = anim.lottie_animation_get_totalframe()
    framerate = anim.lottie_animation_get_framerate()
    
    if framerate <= 0:
        framerate = 30

    with tempfile.TemporaryDirectory() as tmpdir:
        # Рендерим каждый кадр в PNG
        for i in range(total_frames):
            png_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
            anim.save_frame(png_path, frame_num=i)
        
        # Собираем PNG в MP4 с помощью ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-framerate", str(framerate),
            "-i", os.path.join(tmpdir, "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    print(f"!!! ПОЛУЧЕНА КОМАНДА: {message.text} !!!")
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        print("!!! ОШИБКА: НЕТ business_connection_id !!!")
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
        # 1. Удаляем команду
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        # 2. Скачиваем Lottie
        lottie_url = f"https://nft.fragment.com/gift/{gift_slug}.lottie.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(lottie_url) as resp:
                if resp.status != 200:
                    raise Exception("Не удалось скачать анимацию подарка")
                lottie_bytes = await resp.read()

        # 3. Конвертируем в MP4
        mp4_path = f"/tmp/{gift_slug}.mp4"
        convert_lottie_to_mp4(lottie_bytes, mp4_path)
        print("MP4 готов.")

        # 4. Формируем текст и кнопки
        raw_name = gift_slug.split('-')[0]
        pretty_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name) 
        display_name = f"{pretty_name} #{gift_slug.split('-')[-1]}"
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        caption_text = (
            f"<b>Telegram</b>\n"
            f"<b>{display_name}</b>\n\n"
            f"Пользователь {username}\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <b>{pretty_name}</b>."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать подарок", url=link)],
            [
                InlineKeyboardButton(text="Отклонить", callback_data="fake_decline"),
                InlineKeyboardButton(text="Принять", callback_data="fake_accept")
            ]
        ])

        # 5. Отправляем ОДНИМ сообщением: анимация + текст + кнопки
        video_file = FSInputFile(mp4_path)
        await bot.send_animation(
            chat_id=message.chat.id,
            animation=video_file,
            caption=caption_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )
        print("Оффер отправлен одним сообщением!")

        # Удаляем временный файл
        os.remove(mp4_path)

    except Exception as e:
        print(f"!!! ОШИБКА: {e} !!!")
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
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
