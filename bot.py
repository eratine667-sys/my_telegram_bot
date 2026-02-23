import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен берется из переменных окружения!
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = os.getenv('WEBHOOK_URL') + WEBHOOK_PATH

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"👋 Привет, {message.from_user.first_name}!")

# Эхо
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

# Запуск вебхуков
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown():
    await bot.delete_webhook()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, SimpleRequestHandler(dispatcher=dp, bot=bot))
setup_application(app, dp, bot=bot)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
