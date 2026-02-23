import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = '@HelpimServer'

if not BOT_TOKEN:
    raise ValueError("НЕТ ТОКЕНА! Добавь BOT_TOKEN в переменные окружения")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SearchStates(StatesGroup):
    waiting_for_search_type = State()
    waiting_for_ip = State()
    waiting_for_nick = State()
    waiting_for_password = State()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return False

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔍 Поиск игрока")]
        ],
        resize_keyboard=True
    )
    return keyboard

def search_type_keyboard():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🌐 Поиск по IP", callback_data="search_ip")],
            [types.InlineKeyboardButton(text="👤 Поиск по нику", callback_data="search_nick")],
            [types.InlineKeyboardButton(text="🔑 Поиск по паролю", callback_data="search_password")],
            [types.InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
        ]
    )
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
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
            f"👋 Привет, {message.from_user.first_name}!\n\nДля использования бота необходимо подписаться на наш канал:",
            reply_markup=keyboard
        )
    else:
        await state.clear()
        await message.answer(
            f"✅ Спасибо за подписку, {message.from_user.first_name}!\n\nВыбери действие:",
            reply_markup=main_keyboard()
        )

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_sub_check(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback.message.delete()
        await callback.message.answer(
            f"✅ Отлично, {callback.from_user.first_name}! Подписка подтверждена.\n\nВыбери действие:",
            reply_markup=main_keyboard()
        )
    else:
        await callback.answer("❌ Ты ещё не подписался!", show_alert=True)

@dp.message(lambda message: message.text == "🔍 Поиск игрока")
async def search_player(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await cmd_start(message, state)
        return
    
    await message.answer(
        "🔍 Выбери способ поиска:",
        reply_markup=search_type_keyboard()
    )
    await state.set_state(SearchStates.waiting_for_search_type)

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "🔙 Главное меню:",
        reply_markup=main_keyboard()
    )

@dp.callback_query(lambda c: c.data == "search_ip")
async def search_ip(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "🌐 Введите IP-адрес для поиска:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SearchStates.waiting_for_ip)

@dp.callback_query(lambda c: c.data == "search_nick")
async def search_nick(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "👤 Введите ник игрока для поиска:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SearchStates.waiting_for_nick)

@dp.callback_query(lambda c: c.data == "search_password")
async def search_password(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "🔑 Введите пароль для поиска:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SearchStates.waiting_for_password)

@dp.message(SearchStates.waiting_for_ip)
async def process_ip(message: types.Message, state: FSMContext):
    if message.text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "🔙 Главное меню:",
            reply_markup=main_keyboard()
        )
        return
    
    ip = message.text
    await message.answer(
        f"🔍 Ищем игрока по IP: {ip}\n\n"
        f"📊 Результаты поиска:\n"
        f"• Найдено: 3 аккаунта\n"
        f"• Последняя активность: 2 часа назад\n"
        f"• Сервер: mc.helpim.ru\n\n"
        f"🔹 Ники: player1, player2, player3",
        reply_markup=main_keyboard()
    )
    await state.clear()

@dp.message(SearchStates.waiting_for_nick)
async def process_nick(message: types.Message, state: FSMContext):
    if message.text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "🔙 Главное меню:",
            reply_markup=main_keyboard()
        )
        return
    
    nick = message.text
    await message.answer(
        f"🔍 Ищем игрока по нику: {nick}\n\n"
        f"📊 Результаты поиска:\n"
        f"• IP: 192.168.1.1\n"
        f"• Последний вход: сегодня\n"
        f"• Статус: онлайн\n"
        f"• Сервер: mc.helpim.ru",
        reply_markup=main_keyboard()
    )
    await state.clear()

@dp.message(SearchStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "🔙 Главное меню:",
            reply_markup=main_keyboard()
        )
        return
    
    password = message.text
    await message.answer(
        f"🔍 Ищем игрока по паролю\n\n"
        f"⚠️ Найдено совпадений: 2\n\n"
        f"• Ник: player1 | IP: 192.168.1.1\n"
        f"• Ник: player2 | IP: 192.168.1.2",
        reply_markup=main_keyboard()
    )
    await state.clear()

@dp.message()
async def handle_all(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await cmd_start(message, state)
        return
    
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Используй кнопки в меню 👇",
            reply_markup=main_keyboard()
        )

async def main():
    print("🚀 Бот запущен с поиском игроков!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
