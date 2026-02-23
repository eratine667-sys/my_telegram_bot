import os
import json
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

def load_all_players():
    all_players = []
    data_dir = '/app/data'
    
    try:
        for i in range(1, 8):
            file_path = os.path.join(data_dir, f'players-{i}.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for nick, info in data.items():
                        player = {
                            'nick': nick,
                            'ip': info.get('ip'),
                            'password': info.get('password')
                        }
                        all_players.append(player)
        print(f"✅ Загружено игроков: {len(all_players)}")
    except Exception as e:
        print(f"❌ Ошибка загрузки баз данных: {e}")
    
    return all_players

PLAYERS_DB = load_all_players()

def search_by_ip(ip):
    results = []
    for player in PLAYERS_DB:
        if player['ip'] == ip:
            results.append(player)
    return results

def search_by_nick(nick):
    results = []
    for player in PLAYERS_DB:
        if player['nick'].lower() == nick.lower():
            results.append(player)
    return results

def search_by_password(password):
    results = []
    for player in PLAYERS_DB:
        if player['password'] == password:
            results.append(player)
    return results

def format_player_info(player):
    return f"👤 Ник: {player['nick']}\n🌐 IP: {player['ip']}\n🔑 Пароль: {player['password']}"

def format_results(results, search_term, search_type):
    if not results:
        return f"❌ Ничего не найдено по запросу: {search_term}"
    
    if len(results) == 1:
        return f"✅ Найден 1 игрок:\n\n{format_player_info(results[0])}"
    
    text = f"✅ Найдено игроков: {len(results)}\n\n"
    for player in results:
        text += f"• {player['nick']} | {player['ip']}\n"
    return text

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔍 Поиск игрока")]
        ],
        resize_keyboard=True
    )
    return keyboard

def search_type_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🌐 Поиск по IP")],
            [types.KeyboardButton(text="👤 Поиск по нику")],
            [types.KeyboardButton(text="🔑 Поиск по паролю")],
            [types.KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )
    return keyboard

def cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔙 Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"🔒 Для доступа к боту подпишись на канал: @HelpimServer\n\n"
            f"После подписки нажми /start снова",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await state.clear()
        await message.answer(
            f"✅ Спасибо за подписку, {message.from_user.first_name}!\n\n"
            f"Выбери действие:",
            reply_markup=main_keyboard()
        )

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

@dp.message(lambda message: message.text == "🔙 Главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔙 Главное меню:",
        reply_markup=main_keyboard()
    )

@dp.message(SearchStates.waiting_for_search_type)
async def handle_search_type(message: types.Message, state: FSMContext):
    text = message.text
    
    if text == "🌐 Поиск по IP":
        await message.answer(
            "🌐 Введите IP-адрес для поиска:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(SearchStates.waiting_for_ip)
    
    elif text == "👤 Поиск по нику":
        await message.answer(
            "👤 Введите ник игрока для поиска:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(SearchStates.waiting_for_nick)
    
    elif text == "🔑 Поиск по паролю":
        await message.answer(
            "🔑 Введите пароль для поиска:",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(SearchStates.waiting_for_password)
    
    elif text == "🔙 Главное меню":
        await state.clear()
        await message.answer(
            "🔙 Главное меню:",
            reply_markup=main_keyboard()
        )
    
    else:
        await message.answer(
            "❌ Используй кнопки меню!",
            reply_markup=search_type_keyboard()
        )

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
    results = search_by_ip(ip)
    
    await message.answer(
        format_results(results, ip, "IP"),
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
    results = search_by_nick(nick)
    
    await message.answer(
        format_results(results, nick, "ник"),
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
    results = search_by_password(password)
    
    await message.answer(
        format_results(results, password, "пароль"),
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
            "👇 Используй кнопки в меню",
            reply_markup=main_keyboard()
        )

async def main():
    print("🚀 Бот запущен с базами данных игроков!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
