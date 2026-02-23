import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = '@HelpimServer'

if not BOT_TOKEN:
    raise ValueError("НЕТ ТОКЕНА! Добавь BOT_TOKEN в переменные окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/HelpimServer")],
                [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
            ]
        )
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Для использования бота необходимо подписаться на наш канал:",
            reply_markup=keyboard
        )
    else:
        await message.answer(f"✅ Спасибо за подписку, {message.from_user.first_name}! Теперь ты можешь пользоваться ботом.")

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_sub_check(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback.message.edit_text(
            f"✅ Отлично, {callback.from_user.first_name}! Подписка подтверждена. Теперь ты можешь пользоваться ботом."
        )
    else:
        await callback.answer("❌ Ты ещё не подписался на канал! Подпишись и нажми кнопку снова.", show_alert=True)

@dp.message()
async def handle_all(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/HelpimServer")],
                [types.InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
            ]
        )
        await message.answer(
            "❌ Ты не подписан на канал!\n\n"
            "Чтобы пользоваться ботом, подпишись:",
            reply_markup=keyboard
        )
    else:
        await message.answer(f"Ты написал: {message.text}")

async def main():
    print("🚀 Бот запущен и проверяет подписку на канал!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
