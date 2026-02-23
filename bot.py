import os
import json
import datetime
import random
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
WAITING_PROMO_CODE = range(8, 9)
WAITING_PROMO_DAYS = range(9, 10)
WAITING_PROMO_MINUTES = range(10, 11)
WAITING_PROMO_ACTIVATIONS = range(11, 12)

def load_users():
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_promocodes():
    try:
        with open('promocodes.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_promocodes(promocodes):
    with open('promocodes.json', 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=2)

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
    if not expiry_date_str:
        return 0
    if expiry_date_str == 'forever':
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
                    return False
                return True
            except:
                return False
    return False

def get_subscription_status(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str in users:
        expiry = users[user_id_str].get('subscription_end')
        if expiry == 'forever':
            return "✅ Навсегда"
        if expiry:
            try:
                expiry_date = datetime.datetime.fromisoformat(expiry)
                now = datetime.datetime.now()
                if expiry_date < now:
                    return "❌ Нет подписки"
                delta = expiry_date - now
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                if days > 0:
                    return f"✅ {days} дн. {hours} ч."
                elif hours > 0:
                    return f"✅ {hours} ч. {minutes} мин."
                else:
                    return f"✅ {minutes} мин."
            except:
                return "❌ Нет подписки"
    return "❌ Нет подписки"

def add_subscription_time(user_id, minutes):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {
            'joined_date': datetime.datetime.now().isoformat(),
            'subscription_end': None,
            'referrals': 0,
            'referred_by': None,
            'last_wheel': None,
            'last_random': None
        }
    
    current_sub = users[user_id_str].get('subscription_end')
    
    if current_sub == 'forever':
        return
    
    if current_sub:
        sub_date = datetime.datetime.fromisoformat(current_sub)
        if sub_date > datetime.datetime.now():
            new_sub = sub_date + datetime.timedelta(minutes=minutes)
        else:
            new_sub = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    else:
        new_sub = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    
    users[user_id_str]['subscription_end'] = new_sub.isoformat()
    save_users(users)

def add_subscription_days(user_id, days):
    add_subscription_time(user_id, days * 24 * 60)

def can_use_wheel(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        return True
    last_wheel = users[user_id_str].get('last_wheel')
    if not last_wheel:
        return True
    last = datetime.datetime.fromisoformat(last_wheel)
    now = datetime.datetime.now()
    delta = now - last
    return delta.total_seconds() >= 14 * 3600

def can_use_random(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        return True
    last_random = users[user_id_str].get('last_random')
    if not last_random:
        return True
    last = datetime.datetime.fromisoformat(last_random)
    now = datetime.datetime.now()
    delta = now - last
    return delta.total_seconds() >= 14 * 3600

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Поиск игрока")],
        [KeyboardButton("👤 Мой профиль"), KeyboardButton("💰 Заработать")],
        [KeyboardButton("🛒 Магазин"), KeyboardButton("🎮 Игры")]
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

def games_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎡 Колесо удачи", callback_data="wheel")],
        [InlineKeyboardButton("🎲 Рандомный аккаунт", callback_data="random_account")],
        [InlineKeyboardButton("🎫 Промокод", callback_data="promo")]
    ]
    return InlineKeyboardMarkup(keyboard)

def exchange_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔄 Обменять рефералов")]],
        resize_keyboard=True
    )

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
            'first_seen': datetime.datetime.now().isoformat(),
            'last_wheel': None,
            'last_random': None
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
            f"🚀 Приветствуем в нашем боте v0.9.0!\n\n"
            f"Мы долго готовили данное обновление!\n\n"
            f"📋 Доступные функции:\n"
            f"• 🔍 Поиск игроков по базе данных\n"
            f"• 👤 Личный профиль с статистикой\n"
            f"• 💰 Заработок подписки за рефералов\n"
            f"• 🛒 Магазин подписок\n"
            f"• 🎮 Игры и развлечения\n\n"
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
            f"🚀 Приветствуем в нашем боте v0.9.0!\n\n"
            f"Мы долго готовили данное обновление!\n\n"
            f"📋 Доступные функции:\n"
            f"• 🔍 Поиск игроков по базе данных\n"
            f"• 👤 Личный профиль с статистикой\n"
            f"• 💰 Заработок подписки за рефералов\n"
            f"• 🛒 Магазин подписок\n"
            f"• 🎮 Игры и развлечения\n\n"
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
    
    sub_status = get_subscription_status(user_id)
    
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
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=exchange_keyboard())

async def exchange_refs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 Обменять рефералов":
        await update.message.reply_text(
            "💬 Укажи сколько рефералов хочешь обменять:",
            reply_markup=cancel_keyboard()
        )
        return WAITING_REFERRAL_AMOUNT
    return ConversationHandler.END

async def process_referral_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 Отмена":
        await update.message.reply_text("🔙 Главное меню:", reply_markup=main_keyboard())
        return ConversationHandler.END
    
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
        
        add_subscription_time(user_id, minutes)
        
        await update.message.reply_text(
            f"✅ Успешно обменяно {amount} рефералов на {minutes} минут подписки!\n\n"
            f"⏱ Текущий статус: {get_subscription_status(user_id)}",
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
    
    elif query.data == "back_to_shop":
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
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=shop_inline_keyboard())
        return ConversationHandler.END

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

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_channel_sub(user_id, context)
    
    if not is_subscribed:
        await start(update, context)
        return
    
    text = (
        f"🎮 <b>Игры и развлечения</b>\n\n"
        f"Выбери игру:"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=games_inline_keyboard())

async def games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "wheel":
        if not can_use_wheel(user_id):
            users = load_users()
            last_wheel = users[str(user_id)].get('last_wheel')
            last = datetime.datetime.fromisoformat(last_wheel)
            now = datetime.datetime.now()
            delta = now - last
            remaining = 14 * 3600 - delta.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await query.edit_message_text(
                f"❌ Колесо удачи можно использовать раз в 14 часов!\n"
                f"⏳ Осталось: {hours} ч. {minutes} мин.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
            return
        
        if random.random() < 0.5:
            minutes = 5
            add_subscription_time(user_id, minutes)
            
            users = load_users()
            users[str(user_id)]['last_wheel'] = datetime.datetime.now().isoformat()
            save_users(users)
            
            await query.edit_message_text(
                f"🎉 Поздравляем! Ты выиграл {minutes} минут подписки!\n\n"
                f"⏱ Текущий статус: {get_subscription_status(user_id)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
        else:
            users = load_users()
            users[str(user_id)]['last_wheel'] = datetime.datetime.now().isoformat()
            save_users(users)
            
            await query.edit_message_text(
                f"😢 К сожалению, ты ничего не выиграл.\nПопробуй через 14 часов!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
    
    elif query.data == "random_account":
        if not can_use_random(user_id):
            users = load_users()
            last_random = users[str(user_id)].get('last_random')
            last = datetime.datetime.fromisoformat(last_random)
            now = datetime.datetime.now()
            delta = now - last
            remaining = 14 * 3600 - delta.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await query.edit_message_text(
                f"❌ Рандомный аккаунт можно получать раз в 14 часов!\n"
                f"⏳ Осталось: {hours} ч. {minutes} мин.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
            return
        
        if PLAYERS_DB:
            account = random.choice(PLAYERS_DB)
            
            users = load_users()
            users[str(user_id)]['last_random'] = datetime.datetime.now().isoformat()
            save_users(users)
            
            text = (
                f"🎲 <b>Твой случайный аккаунт:</b>\n\n"
                f"👤 Ник: {account['nick']}\n"
                f"🔑 Пароль: {account['password']}\n"
                f"🌐 IP: {account['ip']}"
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
        else:
            await query.edit_message_text(
                "❌ База данных аккаунтов пуста!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
            )
    
    elif query.data == "promo":
        await query.edit_message_text(
            "🎫 Введи промокод:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_games")]])
        )
        return WAITING_PROMO_CODE
    
    elif query.data == "back_to_games":
        await query.edit_message_text(
            f"🎮 <b>Игры и развлечения</b>\n\n"
            f"Выбери игру:",
            parse_mode=ParseMode.HTML,
            reply_markup=games_inline_keyboard()
        )

async def process_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip()
    
    promocodes = load_promocodes()
    
    if code in promocodes:
        promo = promocodes[code]
        if promo['activations'] <= 0:
            await update.message.reply_text("❌ Этот промокод уже использован!", reply_markup=main_keyboard())
            return ConversationHandler.END
        
        if str(user_id) in promo.get('used_by', []):
            await update.message.reply_text("❌ Ты уже использовал этот промокод!", reply_markup=main_keyboard())
            return ConversationHandler.END
        
        if promo['type'] == 'minutes':
            add_subscription_time(user_id, promo['value'])
            text = f"✅ Промокод активирован! Ты получил {promo['value']} минут подписки!"
        elif promo['type'] == 'days':
            add_subscription_days(user_id, promo['value'])
            text = f"✅ Промокод активирован! Ты получил {promo['value']} дней подписки!"
        
        promocodes[code]['activations'] -= 1
        if 'used_by' not in promocodes[code]:
            promocodes[code]['used_by'] = []
        promocodes[code]['used_by'].append(str(user_id))
        save_promocodes(promocodes)
        
        text += f"\n\n⏱ Текущий статус: {get_subscription_status(user_id)}"
        await update.message.reply_text(text, reply_markup=main_keyboard())
