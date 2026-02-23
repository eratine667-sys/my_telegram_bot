import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

# Токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("НЕТ ТОКЕНА! Добавь BOT_TOKEN в переменные окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"👋 Привет, {message.from_user.first_name}!")

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

async def main():
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
