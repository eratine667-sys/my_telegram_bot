import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = '@HelpimServer'

if not BOT_TOKEN:
    raise ValueError("НЕТ ТОКЕНА! Добавь BOT_TOKEN в переменные окружения")

WAITING_SEARCH_TYPE, WAITING_IP, WAITING_NICK, WAITING_PASSWORD = range(4)

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

def main_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔍 Поиск игрока")]],
        resize_keyboard=True
    )

def search_type_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌐 Поиск по IP")],
        [KeyboardButton("👤 Поиск по нику")],
        [KeyboardButton("🔑 Поиск по паролю")],
        [KeyboardButton("🔙 Главное меню")]
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔙 Отмена")]],
        resize_keyboard=True
    )

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context)
    
    if not is_subscribed:
        await update.message.reply_text(
            f"👋 Привет, {update.effective_user.first_name}!\n\n"
            f"🔒 Для доступа к боту подпишись на канал: @HelpimServer\n\n"
            f"После подписки нажми /start снова"
        )
    else:
        await update.message.reply_text(
            f"✅ Спасибо за подписку, {update.effective_user.first_name}!\n\n"
            f"Выбери действие:",
            reply_markup=main_keyboard()
        )
    return ConversationHandler.END

async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Выбери способ поиска:",
        reply_markup=search_type_keyboard()
    )
    return WAITING_SEARCH_TYPE

async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌐 Поиск по IP":
        await update.message.reply_text("🌐 Введи IP:", reply_markup=cancel_keyboard())
        return WAITING_IP
    elif text == "👤 Поиск по нику":
        await update.message.reply_text("👤 Введи ник:", reply_markup=cancel_keyboard())
        return WAITING_NICK
    elif text == "🔑 Поиск по паролю":
        await update.message.reply_text("🔑 Введи пароль:", reply_markup=cancel_keyboard())
        return WAITING_PASSWORD
    elif text == "🔙 Главное меню":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Используй кнопки!", reply_markup=search_type_keyboard())
        return WAITING_SEARCH_TYPE

async def process_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    ip = update.message.text
    results = search_by_ip(ip)
    
    if not results:
        await update.message.reply_text(f"❌ На IP {ip} ничего нет", reply_markup=main_keyboard())
    else:
        text = f"🌐 IP: {ip}\n\n"
        for player in results:
            text += f"👤 Ник: {player['nick']}\n🔑 Пароль: {player['password']}\n\n"
        await update.message.reply_text(text, reply_markup=main_keyboard())
    
    return ConversationHandler.END

async def process_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    nick = update.message.text
    results = search_by_nick(nick)
    
    if not results:
        await update.message.reply_text(f"❌ Ник {nick} не найден", reply_markup=main_keyboard())
    else:
        player = results[0]
        await update.message.reply_text(
            f"👤 Ник: {player['nick']}\n🔑 Пароль: {player['password']}",
            reply_markup=main_keyboard()
        )
    
    return ConversationHandler.END

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    password = update.message.text
    results = search_by_password(password)
    
    if not results:
        await update.message.reply_text(f"❌ Пароль {password} не найден", reply_markup=main_keyboard())
    else:
        text = f"🔑 Пароль: {password}\n\n"
        for player in results:
            text += f"👤 Ник: {player['nick']}\n"
        await update.message.reply_text(text, reply_markup=main_keyboard())
    
    return ConversationHandler.END

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return ConversationHandler.END
    
    await update.message.reply_text("👇 Используй кнопки", reply_markup=main_keyboard())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("🔍 Поиск игрока"), search_player)],
        states={
            WAITING_SEARCH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_type)],
            WAITING_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_ip)],
            WAITING_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_nick)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.Text("🔙 Отмена"), cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all))
    
    print("🚀 Бот запущен на python-telegram-bot")
    app.run_polling()

if __name__ == "__main__":
    main()
