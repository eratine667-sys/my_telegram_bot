import os
import json
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = '@HelpimServer'
ADMIN_ID = 7878666092

if not BOT_TOKEN:
    raise ValueError("НЕТ ТОКЕНА! Добавь BOT_TOKEN в переменные окружения")

WAITING_SEARCH_TYPE, WAITING_IP, WAITING_NICK, WAITING_PASSWORD = range(4)
WAITING_REFERRAL_AMOUNT = range(4, 5)
WAITING_SUB_DAYS = range(5, 6)
WAITING_ADMIN_SUB = range(6, 7)
WAITING_RASS = range(7, 8)

def load_users():
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

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
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
    return all_players

PLAYERS_DB = load_all_players()

def search_by_ip(ip):
    ip = ip.strip()
    results = []
    for player in PLAYERS_DB:
        if player['ip'] == ip:
            results.append(player)
    return results

def search_by_nick_partial(nick_part):
    nick_part = nick_part.strip().lower()
    results = []
    for player in PLAYERS_DB:
        if player['nick'].lower().startswith(nick_part):
            results.append(player)
    return results

def search_by_password_partial(password_part):
    password_part = password_part.strip().lower()
    results = []
    for player in PLAYERS_DB:
        if player['password'] and password_part in player['password'].lower():
            results.append(player)
    return results

def calculate_sub_price(days):
    if days == 1: return 125
    elif days == 7: return 350
    elif days == 14: return 650
    elif days == 30: return 950
    elif days == 9999: return 3150
    else: return days * 44

def calculate_ref_bonus(refs):
    if refs >= 100: return "30 дней"
    elif refs >= 50: return "7 дней"
    elif refs >= 35: return "1 день"
    elif refs >= 25: return "30 минут"
    elif refs >= 10: return "15 минут"
    else:
        minutes = refs * 2
        return f"{minutes} минут"

def days_until_expiry(expiry_date_str):
    if not expiry_date_str or expiry_date_str == 'forever':
        return 9999
    try:
        expiry = datetime.datetime.fromisoformat(expiry_date_str)
        now = datetime.datetime.now()
        delta = expiry - now
        return max(0, delta.days)
    except:
        return 0

def check_sub_expiry(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str in users:
        expiry = users[user_id_str].get('subscription_end')
        if expiry == 'forever':
            return True
        if expiry:
            try:
                expiry_date = datetime.datetime.fromisoformat(expiry)
                if expiry_date < datetime.datetime.now():
                    users[user_id_str]['subscription_end'] = None
                    save_users(users)
                    return False
                return True
            except:
                return False
    return False

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Поиск игрока")],
        [KeyboardButton("👤 Мой профиль"), KeyboardButton("💰 Заработать")],
        [KeyboardButton("🛒 Магазин")]
    ], resize_keyboard=True)

def search_type_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌐 Поиск по IP"), KeyboardButton("👤 Поиск по нику")],
        [KeyboardButton("🔑 Поиск по паролю"), KeyboardButton("🔙 Главное меню")]
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔙 Отмена")]],
        resize_keyboard=True
    )

def earn_inline_keyboard():
    keyboard = [[InlineKeyboardButton("💰 Заработать подписку", callback_data="earn_sub")]]
    return InlineKeyboardMarkup(keyboard)

def exchange_inline_keyboard():
    keyboard = [[InlineKeyboardButton("🔄 Обменять рефералов", callback_data="exchange_refs")]]
    return InlineKeyboardMarkup(keyboard)

def shop_inline_keyboard():
    keyboard = [[InlineKeyboardButton("🎁 Приобрести подписку", callback_data="buy_sub")]]
    return InlineKeyboardMarkup(keyboard)

async def check_channel_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return False

def update_user_activity(user_id, username=None):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            'joined_date': datetime.datetime.now().isoformat(),
            'subscription_end': None,
            'referrals': 0,
            'referred_by': None,
            'username': username,
            'first_seen': datetime.datetime.now().isoformat()
        }
    else:
        users[user_id_str]['last_seen'] = datetime.datetime.now().isoformat()
        if username:
            users[user_id_str]['username'] = username
    save_users(users)
    return users[user_id_str]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    if context.args and len(context.args) > 0:
        referrer_id = context.args[0]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            context.user_data['referred_by'] = referrer_id
    
    update_user_activity(user_id, username)
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")]
        ])
        await update.message.reply_text(
            f"👋 Привет, {first_name}!\n\n"
            f"🔒 Для доступа к боту подпишись на канал: {CHANNEL_ID}\n\n"
            f"После подписки нажми кнопку ниже:",
            reply_markup=keyboard
        )
    else:
        if 'referred_by' in context.user_data:
            referrer_id = context.user_data['referred_by']
            users = load_users()
            if str(referrer_id) in users:
                users[str(referrer_id)]['referrals'] = users[str(referrer_id)].get('referrals', 0) + 1
                save_users(users)
                try:
                    await context.bot.send_message(
                        int(referrer_id),
                        f"🎉 У вас новый реферал! Теперь у вас {users[str(referrer_id)]['referrals']} рефералов."
                    )
                except:
                    pass
            del context.user_data['referred_by']
        
        await update.message.reply_text(
            f"🚀 Приветствуем в нашем боте v0.8.1!\n\n"
            f"Мы долго готовили данное обновление!\n\n"
            f"📋 Доступные функции:\n"
            f"• 🔍 Поиск игроков по базе данных\n"
            f"• 👤 Личный профиль с статистикой\n"
            f"• 💰 Заработок подписки за рефералов\n"
            f"• 🛒 Магазин подписок\n\n"
            f"Выбирай функцию кнопками ниже:",
            reply_markup=main_keyboard()
        )
    return ConversationHandler.END

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if is_subscribed:
        await query.edit_message_text(
            f"🚀 Приветствуем в нашем боте v0.8.1!\n\n"
            f"Мы долго готовили данное обновление!\n\n"
            f"📋 Доступные функции:\n"
            f"• 🔍 Поиск игроков по базе данных\n"
            f"• 👤 Личный профиль с статистикой\n"
            f"• 💰 Заработок подписки за рефералов\n"
            f"• 🛒 Магазин подписок\n\n"
            f"Выбирай функцию кнопками ниже:"
        )
        await query.message.reply_text("👇 Твои кнопки:", reply_markup=main_keyboard())
    else:
        await query.answer("❌ Ты ещё не подписался!", show_alert=True)

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    is_subscribed = await check_channel_sub(user_id, context)
    if not is_subscribed:
        await start(update, context)
        return
    
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        user_data = update_user_activity(user_id, username)
    else:
        user_data = users[user_id_str]
    
    joined = datetime.datetime.fromisoformat(user_data.get('joined_date', datetime.datetime.now().isoformat()))
    days_in_bot = (datetime.datetime.now() - joined).days
    
    sub_end = user_data.get('subscription_end')
    if sub_end == 'forever':
        sub_status = "✅ Навсегда"
    elif sub_end:
        sub_days = days_until_expiry(sub_end)
        if sub_days > 0 and sub_days < 9999:
            sub_status = f"✅ Активна (осталось {sub_days} дн.)"
        else:
            sub_status = "❌ Нет подписки"
    else:
        sub_status = "❌ Нет подписки"
    
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Username: @{username if username else 'нет'}\n"
        f"📅 В боте: {days_in_bot} дн.\n"
        f"🎫 Подписка: {sub_status}\n"
        f"👥 Рефералов: {user_data.get('referrals', 0)}\n\n"
        f"🔗 Твоя реферальная ссылка:\n"
        f"<code>{ref_link}</code>"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())

async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return ConversationHandler.END
    
    has_sub = check_sub_expiry(user_id)
    if not has_sub:
        await update.message.reply_text(
            "❌ У тебя нет активной подписки!\nКупи или заработай подписку в магазине.",
            reply_markup=main_keyboard()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Выбери способ поиска:",
        reply_markup=search_type_keyboard()
    )
    return WAITING_SEARCH_TYPE

async def handle_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌐 Поиск по IP":
        await update.message.reply_text("🌐 Введи полный IP-адрес:", reply_markup=cancel_keyboard())
        return WAITING_IP
    elif text == "👤 Поиск по нику":
        await update.message.reply_text("👤 Введи начало ника (минимум 3 символа):", reply_markup=cancel_keyboard())
        return WAITING_NICK
    elif text == "🔑 Поиск по паролю":
        await update.message.reply_text("🔑 Введи часть пароля (минимум 3 символа):", reply_markup=cancel_keyboard())
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
            text += f"👤 Ник: {player['nick']}\n🔑 Пароль: {player['password']}\n━━━━━━━━━━━━━━\n"
        await update.message.reply_text(text, reply_markup=main_keyboard())
    
    return ConversationHandler.END

async def process_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    nick_part = update.message.text
    if len(nick_part) < 3:
        await update.message.reply_text("❌ Минимум 3 символа!", reply_markup=cancel_keyboard())
        return WAITING_NICK
    
    results = search_by_nick_partial(nick_part)
    
    if not results:
        await update.message.reply_text(f"❌ Ник начинающийся на '{nick_part}' не найден", reply_markup=main_keyboard())
    else:
        text = f"👤 Ники начинающиеся на '{nick_part}':\n\n"
        for player in results[:10]:
            text += f"👤 {player['nick']}\n🔑 {player['password']}\n━━━━━━━━━━━━━━\n"
        if len(results) > 10:
            text += f"\n... и ещё {len(results)-10}"
        await update.message.reply_text(text, reply_markup=main_keyboard())
    
    return ConversationHandler.END

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
    password_part = update.message.text
    if len(password_part) < 3:
        await update.message.reply_text("❌ Минимум 3 символа!", reply_markup=cancel_keyboard())
        return WAITING_PASSWORD
    
    results = search_by_password_partial(password_part)
    
    if not results:
        await update.message.reply_text(f"❌ Пароль содержащий '{password_part}' не найден", reply_markup=main_keyboard())
    else:
        text = f"🔑 Пароли содержащие '{password_part}':\n\n"
        for player in results[:10]:
            text += f"👤 {player['nick']}\n🔑 {player['password']}\n━━━━━━━━━━━━━━\n"
        if len(results) > 10:
            text += f"\n... и ещё {len(results)-10}"
        await update.message.reply_text(text, reply_markup=main_keyboard())
    
    return ConversationHandler.END

async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return
    
    users = load_users()
    user_data = users.get(str(user_id), {})
    referrals = user_data.get('referrals', 0)
    bonus = calculate_ref_bonus(referrals)
    
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    text = (
        f"💰 <b>Заработок подписки</b>\n\n"
        f"👥 Твои рефералы: {referrals}\n"
        f"🎁 Ты можешь получить: {bonus}\n\n"
        f"<b>Тарифы обмена:</b>\n"
        f"• 10 рефералов → 15 минут\n"
        f"• 25 рефералов → 30 минут\n"
        f"• 35 рефералов → 1 день\n"
        f"• 50 рефералов → 7 дней\n"
        f"• 100 рефералов → 30 дней\n\n"
        f"<i>Дополнительно: можно обменять любое количество рефералов (1 реферал = 2 минуты)</i>\n\n"
        f"🔗 Твоя реферальная ссылка:\n"
        f"<code>{ref_link}</code>"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=earn_inline_keyboard())

async def earn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "earn_sub":
        text = (
            f"🎁 <b>Заработок подписки</b>\n\n"
            f"Привет! Ты можешь заработать подписку в нашем боте "
            f"и использовать полный функционал.\n\n"
            f"<b>Тарифы обмена:</b>\n"
            f"• 10 рефералов → 15 минут\n"
            f"• 25 рефералов → 30 минут\n"
            f"• 35 рефералов → 1 день\n"
            f"• 50 рефералов → 7 дней\n"
            f"• 100 рефералов → 30 дней\n\n"
            f"<i>Каждый реферал даёт 2 минуты подписки</i>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=exchange_inline_keyboard())
    
    elif query.data == "exchange_refs":
        await query.edit_message_text(
            "💬 Укажи сколько рефералов хочешь обменять:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="earn_sub")]])
        )
        return WAITING_REFERRAL_AMOUNT

async def process_referral_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
        user_id = update.effective_user.id
        users = load_users()
        user_data = users.get(str(user_id), {})
        referrals = user_data.get('referrals', 0)
        
        if amount <= 0 or amount > referrals:
            await update.message.reply_text(f"❌ У тебя только {referrals} рефералов!", reply_markup=main_keyboard())
            return ConversationHandler.END
        
        minutes = amount * 2
        users[str(user_id)]['referrals'] = referrals - amount
        
        current_sub = user_data.get('subscription_end')
        if current_sub == 'forever':
            new_sub = 'forever'
        elif current_sub:
            sub_date = datetime.datetime.fromisoformat(current_sub)
            new_sub = (sub_date + datetime.timedelta(minutes=minutes)).isoformat()
        else:
            new_sub = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
        
        users[str(user_id)]['subscription_end'] = new_sub
        save_users(users)
        
        await update.message.reply_text(
            f"✅ Успешно обменяно {amount} рефералов на {minutes} минут подписки!",
            reply_markup=main_keyboard()
        )
    except ValueError:
        await update.message.reply_text("❌ Введи число!", reply_markup=cancel_keyboard())
        return WAITING_REFERRAL_AMOUNT
    
    return ConversationHandler.END

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return
    
    text = (
        f"🛒 <b>Магазин подписок</b>\n\n"
        f"<b>Цены:</b>\n"
        f"• 1 день — 125₽\n"
        f"• 7 дней — 350₽\n"
        f"• 14 дней — 650₽\n"
        f"• 30 дней — 950₽\n"
        f"• Навсегда — 3150₽\n\n"
        f"<i>Если нужна подписка на другое количество дней — каждый день +44₽</i>"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=shop_inline_keyboard())

async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_sub":
        await query.edit_message_text(
            "💬 Сколько дней подписки нужно? (9999 для навсегда)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_shop")]])
        )
        return WAITING_SUB_DAYS

async def process_sub_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text)
        if days <= 0:
            await update.message.reply_text("❌ Введи положительное число!", reply_markup=cancel_keyboard())
            return WAITING_SUB_DAYS
        
        price = calculate_sub_price(days)
        days_text = "навсегда" if days == 9999 else f"{days} дней"
        
        text = (
            f"💰 <b>Заказ подписки</b>\n\n"
            f"📅 Дней: {days_text}\n"
            f"💵 Цена: {price}₽\n\n"
            f"<b>Отлично! Для приобретения подписки напиши админу:</b>\n"
            f"👤 @loqin_win\n\n"
            f"<code>Привет! Хочу купить подписку на {days_text} за {price}₽</code>"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
        
        await context.bot.send_message(
            ADMIN_ID,
            f"🛒 Новый заказ!\nОт: {update.effective_user.first_name} (@{update.effective_user.username})\nID: {update.effective_user.id}\nДней: {days_text}\nЦена: {price}₽"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Введи число!", reply_markup=cancel_keyboard())
        return WAITING_SUB_DAYS
    
    return ConversationHandler.END

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав администратора!")
        return
    
    text = (
        f"👑 <b>Админ панель</b>\n\n"
        f"<b>Команды:</b>\n"
        f"• /stat - статистика бота\n"
        f"• /sub - выдать подписку\n"
        f"• /rass - рассылка"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def admin_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    users = load_users()
    active_subs = 0
    total_refs = 0
    
    for uid, data in users.items():
        if data.get('subscription_end'):
            if data['subscription_end'] == 'forever' or days_until_expiry(data['subscription_end']) > 0:
                active_subs += 1
        total_refs += data.get('referrals', 0)
    
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"✅ Активных подписок: {active_subs}\n"
        f"👥 Всего рефералов: {total_refs}\n"
        f"📁 Игроков в базе: {len(PLAYERS_DB)}"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def admin_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = (
        f"👑 <b>Выдача подписки</b>\n\n"
        f"Введи данные в формате:\n"
        f"<code>ID_пользователя ТИП_ПОДПИСКИ</code>\n\n"
        f"<b>Типы подписки:</b>\n"
        f"• 1_day - 1 день\n"
        f"• 7_days - 7 дней\n"
        f"• 30_days - 30 дней\n"
        f"• forever - навсегда\n\n"
        f"<i>Пример: 123456789 7_days</i>"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return WAITING_ADMIN_SUB

async def process_admin_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        
        user_id, sub_type = parts
        
        days_map = {
            '1_day': 1,
            '7_days': 7,
            '30_days': 30,
            'forever': 9999
        }
        
        if sub_type not in days_map:
            await update.message.reply_text("❌ Неверный тип подписки!")
            return WAITING_ADMIN_SUB
        
        days = days_map[sub_type]
        
        users = load_users()
        if user_id not in users:
            users[user_id] = {'joined_date': datetime.datetime.now().isoformat()}
        
        if days == 9999:
            users[user_id]['subscription_end'] = 'forever'
        else:
            sub_end = datetime.datetime.now() + datetime.timedelta(days=days)
            users[user_id]['subscription_end'] = sub_end.isoformat()
        
        save_users(users)
        
        await update.message.reply_text(f"✅ Подписка выдана пользователю {user_id}")
        
        try:
            days_text = "навсегда" if days == 9999 else f"{days} дней"
            await context.bot.send_message(
                int(user_id),
                f"🎉 Вам выдана подписка на {days_text}!"
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return WAITING_ADMIN_SUB
    
    return ConversationHandler.END

async def admin_rass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("📨 Введи текст для рассылки:")
    return WAITING_RASS

async def process_rass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    text = update.message.text
    users = load_users()
    
    sent = 0
    failed = 0
    
    await update.message.reply_text(f"📨 Начинаю рассылку {len(users)} пользователям...")
    
    for user_id in users.keys():
        try:
            await context.bot.send_message(int(user_id), text)
            sent += 1
        except:
            failed += 1
    
    await update.message.reply_text(f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return
    
    text = update.message.text
    
    if text == "👤 Мой профиль":
        await my_profile(update, context)
    elif text == "💰 Заработать":
        await earn(update, context)
    elif text == "🛒 Магазин":
        await shop(update, context)
    elif text == "🔍 Поиск игрока":
        await search_player(update, context)
    else:
        await update.message.reply_text("👇 Используй кнопки в меню", reply_markup=main_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    search_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("🔍 Поиск игрока"), search_player)],
        states={
            WAITING_SEARCH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_type)],
            WAITING_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_ip)],
            WAITING_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_nick)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.Text("🔙 Отмена"), cancel)]
    )
    
    ref_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(earn_callback, pattern="^exchange_refs$")],
        states={
            WAITING_REFERRAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_referral_exchange)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    buy_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(shop_callback, pattern="^buy_sub$")],
        states={
            WAITING_SUB_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_sub_days)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    admin_sub_conv = ConversationHandler(
        entry_points=[CommandHandler("sub", admin_sub)],
        states={
            WAITING_ADMIN_SUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_sub)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    admin_rass_conv = ConversationHandler(
        entry_points=[CommandHandler("rass", admin_rass)],
        states={
            WAITING_RASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_rass)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stat", admin_stat))
    app.add_handler(admin_sub_conv)
    app.add_handler(admin_rass_conv)
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(earn_callback, pattern="^(earn_sub|exchange_refs)$"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern="^(buy_sub|back_to_shop)$"))
    app.add_handler(search_conv)
    app.add_handler(ref_conv)
    app.add_handler(buy_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all))
    
    print("🚀 Бот запущен с полным функционалом!")
    app.run_polling()

if __name__ == "__main__":
    main()
