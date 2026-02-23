import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен берется из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN в переменных окружения!")

# Настройки вебхука
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = os.getenv('WEBHOOK_URL') + WEBHOOK_PATH

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Я успешно запущен на Bothost.ru!"
    )

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 Доступные команды:\n"
        "/start - Начать работу\n"
        "/help - Это сообщение\n"
        "Просто напиши что-нибудь - я отвечу!"
    )

# Эхо на все сообщения
@dp.message()
async def echo_all(message: Message):
    await message.answer(f"Ты написал: {message.text}")

# Настройка вебхуков
async def handle_webhook(request):
    update = types.Update(**await request.json())
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Вебхук установлен на {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    print("❌ Вебхук удален")

# Запуск приложения
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(lambda _: on_startup())
app.on_shutdown.append(lambda _: on_shutdown())

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print(f"🚀 Бот запускается на порту {port}")
    web.run_app(app, host='0.0.0.0', port=port)
