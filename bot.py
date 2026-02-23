import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен берется из переменных окружения (которые вы укажете в панели деплоя)
BOT_TOKEN = os.getenv('8256489019:AAEIMe5Txky7M2k4V2SCg_FPsz2FgLD581A')
# WEBHOOK_URL тоже из переменных окружения
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = os.getenv('WEBHOOK_URL') + WEBHOOK_PATH

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Я ваш новый бот, развернутый на хостинге!"
    )

# Эхо на любое текстовое сообщение (для проверки)
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

# Функции для вебхуков
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Вебхук установлен на {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    print("Вебхук удален")

# Настройка aiohttp сервера
app = web.Application()
app.router.add_post(WEBHOOK_PATH, SimpleRequestHandler(
    dispatcher=dp,
    bot=bot
))
setup_application(app, dp, bot=bot)

# Запуск
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
