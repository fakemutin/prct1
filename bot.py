# ============================================================
# 🤖 CRYPTO COINREF BOT – ВЕРСИЯ 123.0 (ВСЁ НОВЫЕ СООБЩЕНИЯ)
# ============================================================

import telebot
import sqlite3
import json
import random
import string
import re
import time
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ============================================================
# 1. КОНФИГУРАЦИЯ
# ============================================================
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        default = {
        "telegramBotToken": "YOUR_BOT_TOKEN_HERE",
        "admin": "8706729447",
        "moderators": "",
        "currency": "₽",
        "minAmount": 10.0,
        "hellomsg": "🌟 Добро пожаловать в CRYPTO COINREF!\n\nЗдесь вы можете зарабатывать, инвестировать, торговать криптовалютой CRF и участвовать в дуэлях.\nИспользуйте кнопки меню для навигации.",
        "subscribemsg": "📢 Подпишитесь на каналы, чтобы получить доступ ко всем функциям!",
        "replenish_card": "5599002061187136",
        "replenish_holder": "Иванов Иван Иванович",
        "replenish_bank": "Сбербанк",
        "requiredChannels": "@COINREF_OFFICIAL",
        "priceperhour": 50.0,
        "priceperuser": 0.3,
        "warning_limit": 3,
        "channel_to_track": "@COINREF_OFFICIAL",
        "log_chat_id": 0,
        "exp_per_bonus": 5,
        "exp_per_spin": 3,
        "exp_per_referral": 10,
        "exp_per_withdraw": 20,
        "exp_per_duel_win": 5,
        "exp_per_task": 15,
        "duel_commission": 8.0,
        "elo_k_factor": 32,
        "elo_default": 1200,
        "duel_min_level": 2,
        "duel_daily_limit_base": 3,
        "season_duration_days": 30,
        "withdraw_min_level": 2,
        "investment_min": 10.0,
        "investment_max_base": 500.0,
        "investment_rates": {"1": 0.05, "3": 0.10, "7": 0.15},
        "daily_tasks_count": 3,
        "vip_price_rub": 100.0,
        "vip_duration_days": 30,
        "crf_initial_rate": 0.01,
        "crf_max_supply": 100000000,
        "crf_staking_rates": {"7": 0.10, "14": 0.15, "30": 0.20},
        "market_commission": 0.20,
        "vip_market_commission": 0.05,
        "referral_crf": {"1": 0.35, "2": 0.70, "3": 1.15},
        "bonus_min_crf": 0.1,
        "bonus_max_crf": 2.0,
        "spin_rewards_crf": [0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0],
        "commission_crf_percent": 20.0,
        "promo_channel_price_per_hour": 50.0,
        "promo_mailing_price_per_user": 0.3,
        "exchange_commission_percent": 10.0
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
            return default

    CONFIG = load_config()
    TOKEN = CONFIG['telegramBotToken']
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Укажите токен в config.json")
        exit(1)

        ADMIN_IDS = [int(x.strip()) for x in CONFIG['admin'].split(',') if x.strip()]
        MODERATOR_IDS = [int(x.strip()) for x in CONFIG.get('moderators', '').split(',') if x.strip()]
        LOG_CHAT_ID = CONFIG.get('log_chat_id', 0)

        # ============================================================
        # 2. БАЗА ДАННЫХ (ПОЛНАЯ)
        # ============================================================
        db = sqlite3.connect('data.db', check_same_thread=False)
        db.row_factory = sqlite3.Row

def get_cursor():
    return db.cursor()

def init_db():
    c = get_cursor()
    # Все таблицы (как в предыдущей версии)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
    chatId INTEGER PRIMARY KEY,
    firstName TEXT,
    username TEXT,
    balance REAL DEFAULT 0,
    referer INTEGER DEFAULT -1,
    is_verified INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    elo_rating INTEGER DEFAULT 1200,
    ref_level INTEGER DEFAULT 1,
    lastDailyBonus TEXT,
    lastSpin TEXT,
    warnings INTEGER DEFAULT 0,
    duel_blocked_until TEXT,
    verification_code TEXT,
    vip_until TEXT,
    daily_tasks_date TEXT,
    daily_tasks_done TEXT,
    vip_active INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdraws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chatId INTEGER,
    amount REAL,
    wallet TEXT,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chatId INTEGER,
    amount REAL,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ownerId INTEGER,
    creationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hours INTEGER,
    channel TEXT,
    title TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE,
    activations INTEGER,
    sum REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promocodeactivations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT,
    userId INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT,
    reward REAL,
    active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (
    user_id INTEGER,
    task_id INTEGER,
    PRIMARY KEY (user_id, task_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER,
    opponent_id INTEGER DEFAULT -1,
    amount REAL,
    mode TEXT DEFAULT 'classic',
    status TEXT DEFAULT 'waiting',
    winner_id INTEGER DEFAULT -1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    elo_creator INTEGER DEFAULT 1200,
    elo_opponent INTEGER DEFAULT 1200,
    creator_choice TEXT,
    opponent_choice TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    prize_pool REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS season_winners (
    season_id INTEGER,
    user_id INTEGER,
    place INTEGER,
    reward REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    term_days INTEGER,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    profit REAL DEFAULT 0,
    currency TEXT DEFAULT 'crf'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_text TEXT,
    task_type TEXT,
    target INTEGER,
    reward_exp INTEGER,
    reward_money REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_daily_progress (
    user_id INTEGER,
    task_id INTEGER,
    progress INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    claimed INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, task_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_balances (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_type TEXT,
    amount REAL,
    price REAL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buy_order_id INTEGER,
    sell_order_id INTEGER,
    amount REAL,
    price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_rate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate REAL DEFAULT 0.01,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS crf_stakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    term_days INTEGER,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    profit REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS moderator_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    moderator_id INTEGER,
    action_type TEXT,
    target_user_id INTEGER,
    data TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    admin_response TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    channel TEXT,
    message TEXT,
    price REAL,
    hours INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promo_subscriptions (
    user_id INTEGER,
    channel TEXT,
    PRIMARY KEY (user_id, channel)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
    key TEXT PRIMARY KEY,
    value REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
    )''')
    for key in ['replenish_card', 'replenish_holder', 'replenish_bank']:
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, CONFIG.get(key, '')))
    for key in ['total_users', 'total_rub_volume', 'total_crf_volume',
                'commission_duel_rub', 'commission_market_rub', 'commission_exchange_rub',
                'commission_exchange_crf', 'commission_invest_crf']:
        c.execute('INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)', (key,))
    db.commit()
    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    for col in ['level','exp','elo_rating','ref_level','vip_until','daily_tasks_date','daily_tasks_done','duel_blocked_until','warnings','is_banned','verification_code','vip_active']:
        if col not in cols:
            c.execute(f'ALTER TABLE users ADD COLUMN {col}')
    c.execute("PRAGMA table_info(duels)")
    duel_cols = [row[1] for row in c.fetchall()]
    for col in ['mode','creator_choice','opponent_choice','elo_creator','elo_opponent']:
        if col not in duel_cols:
            c.execute(f'ALTER TABLE duels ADD COLUMN {col}')
    c.execute('SELECT COUNT(*) FROM crf_rate')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO crf_rate (rate) VALUES (?)', (CONFIG.get('crf_initial_rate', 0.01),))
    c.execute("PRAGMA table_info(user_daily_progress)")
    cols = [row[1] for row in c.fetchall()]
    if 'claimed' not in cols:
        c.execute('ALTER TABLE user_daily_progress ADD COLUMN claimed INTEGER DEFAULT 0')
    db.commit()
    print("✅ База данных готова")

init_db()

# ============================================================
# 3. БОТ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
bot = telebot.TeleBot(TOKEN)
try:
    botUsername = bot.get_me().username
except:
    botUsername = 'CRYPTO_COINREF_BOT'

user_states = {}

def safe_send(chat_id, text, parse_mode=None, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None

def safe_answer(call_id, text=None, alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=alert)
    except:
        pass

def send_log(msg):
    if LOG_CHAT_ID:
        try:
            bot.send_message(LOG_CHAT_ID, msg, parse_mode='HTML')
        except:
            pass

def log_action(user_id, action, details=''):
    user = get_user(user_id)
    name = user['firstName'] if user else str(user_id)
    rub = get_balance_rub(user_id)
    crf = get_balance_crf(user_id)
    c = get_cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE referer = ?', (user_id,))
    refs = c.fetchone()[0] or 0
    msg = f"📋 ЛОГ ДЕЙСТВИЙ\n\n👤 Ник: {name}\n🆔 Айди: {user_id}\n⚡ Действие: {action}\n"
    if details:
        msg += f"📝 Подробности: {details}\n"
        msg += f"👪 Рефералы: {refs}\n💰 Баланс ₽: {rub:.2f}\n💎 Баланс CRF: {crf:.2f}"
        send_log(msg)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_moderator(user_id):
    return user_id in MODERATOR_IDS or is_admin(user_id)

def get_user(user_id):
    c = get_cursor()
    c.execute('SELECT * FROM users WHERE chatId = ?', (user_id,))
    return c.fetchone()

def get_balance_rub(user_id):
    c = get_cursor()
    c.execute('SELECT balance FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    return row['balance'] if row else 0.0

def get_balance_crf(user_id):
    c = get_cursor()
    c.execute('SELECT balance FROM crf_balances WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    return row['balance'] if row else 0.0

def update_balance_rub(user_id, amount):
    c = get_cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE chatId = ?', (amount, user_id))
    db.commit()

def update_balance_crf(user_id, amount):
    c = get_cursor()
    c.execute('''
    INSERT INTO crf_balances (user_id, balance)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    ''', (user_id, amount, amount))
    db.commit()

def add_transaction_rub(user_id, amount, trans_type, desc=''):
    update_balance_rub(user_id, amount)
    c = get_cursor()
    c.execute('INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
    (user_id, amount, trans_type, desc))
    db.commit()
    if amount > 0:
        c.execute('UPDATE stats SET value = value + ? WHERE key = "total_rub_volume"', (amount,))
        db.commit()

def add_transaction_crf(user_id, amount, trans_type, desc=''):
    update_balance_crf(user_id, amount)
    c = get_cursor()
    c.execute('INSERT INTO crf_transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
    (user_id, amount, trans_type, desc))
    db.commit()
    if amount > 0:
        c.execute('UPDATE stats SET value = value + ? WHERE key = "total_crf_volume"', (amount,))
        db.commit()

def apply_crf_commission(user_id, amount):
    if amount <= 0:
        return 0.0
    commission_percent = CONFIG.get('commission_crf_percent', 20.0)
    commission = amount * (commission_percent / 100.0)
    balance = get_balance_crf(user_id)
    if balance < amount + commission:
        return -1.0
    add_transaction_crf(0, commission, 'commission_crf', f'Комиссия 20% при трате {amount:.2f} CRF')
    add_transaction_crf(user_id, -commission, 'commission_crf', f'Комиссия 20% при трате {amount:.2f} CRF')
    c = get_cursor()
    c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_invest_crf"', (commission,))
    db.commit()
    return commission

def get_field(user_id, field, default=0):
    c = get_cursor()
    c.execute(f'SELECT {field} FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    return row[field] if row else default

def update_field(user_id, field, value):
    c = get_cursor()
    c.execute(f'UPDATE users SET {field} = ? WHERE chatId = ?', (value, user_id))
    db.commit()

def clean_channel(ch):
    return re.sub(r'^@|https?://t\.me/', '', ch).strip()

def make_id(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def get_level_config(level):
    return level * 50

def add_exp(user_id, amount):
    if amount <= 0:
        return
    c = get_cursor()
    c.execute('SELECT level, exp FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    if not row:
        return
    level, exp = row['level'], row['exp']
    exp += amount
    while exp >= get_level_config(level):
        exp -= get_level_config(level)
        level += 1
        safe_send(user_id, f"🎉 Поздравляем! Вы достигли {level} уровня!", parse_mode='HTML')
        c.execute('UPDATE users SET level = ?, exp = ? WHERE chatId = ?', (level, exp, user_id))
        db.commit()

def get_user_level(user_id):
    c = get_cursor()
    c.execute('SELECT level, exp FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    if row:
        return (row['level'], row['exp'])
    else:
        return (1, 0)

def get_level_bonuses(level):
    return {
    'bonus_max_crf': min(2.0, 0.1 + level * 0.2),
    'spin_max_crf': min(2.0, 0.1 + level * 0.2),
    'investment_max_rub': CONFIG.get('investment_max_base', 500) + level * 50,
    'investment_max_crf': (CONFIG.get('investment_max_base', 500) + level * 50) * 10,
    'withdraw_fee': max(0, 5 - level * 0.5),
    'duel_limit': CONFIG.get('duel_daily_limit_base', 3) + level * 2,
    'ref_bonus_multiplier': 1 + (level - 1) * 0.05
    }

def is_vip(user_id):
    vip_active = get_field(user_id, 'vip_active', 0)
    if not vip_active:
        return False
    vip_until = get_field(user_id, 'vip_until', None)
    if not vip_until:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(vip_until)
    except:
        return False

def get_vip_remaining(user_id):
    vip_until = get_field(user_id, 'vip_until', None)
    if not vip_until:
        return 0
    try:
        delta = datetime.fromisoformat(vip_until) - datetime.now()
        return max(0, delta.total_seconds())
    except:
        return 0

def buy_vip(user_id):
    if is_vip(user_id):
        return False, "❌ У вас уже активен VIP. Вы можете продлить, но это будет считаться как новая покупка (срок добавится)."
    price = CONFIG.get('vip_price_rub', 100.0)
    if get_balance_rub(user_id) < price:
        return False, f"❌ Недостаточно ₽. Нужно {price:.2f}"
    add_transaction_rub(user_id, -price, 'vip_purchase', f'Покупка VIP на 30 дней (за ₽)')
    days = CONFIG.get('vip_duration_days', 30)
    now = datetime.now()
    new_end = now + timedelta(days=days)
    update_field(user_id, 'vip_until', new_end.isoformat())
    update_field(user_id, 'vip_active', 1)
    return True, f"✅ VIP активирован до {new_end.strftime('%d.%m.%Y %H:%M')}!"

def format_time_remaining(seconds):
    if seconds <= 0:
        return "0мин"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    return f"{minutes}мин"

def get_crf_rate():
    c = get_cursor()
    c.execute('SELECT rate FROM crf_rate ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    return row['rate'] if row else CONFIG.get('crf_initial_rate', 0.01)

def update_crf_rate(new_rate):
    c = get_cursor()
    c.execute('INSERT INTO crf_rate (rate) VALUES (?)', (new_rate,))
    db.commit()

def get_rank(elo):
    if elo >= 2200:
        return "Грандмастер", "👑"
    elif elo >= 2000:
        return "Мастер", "🏆"
    elif elo >= 1800:
        return "Алмаз", "💎"
    elif elo >= 1600:
        return "Платина", "💠"
    elif elo >= 1400:
        return "Золото", "🥇"
    elif elo >= 1200:
        return "Серебро", "🥈"
    else:
        return "Бронза", "🥉"

    # ============================================================
    # 4. РЫНОК (с обновлением статистики комиссий)
    # ============================================================
def get_commission_rate(user_id):
    if is_vip(user_id):
        return CONFIG.get('vip_market_commission', 0.05)
    return CONFIG.get('market_commission', 0.20)

def create_order(user_id, order_type, amount, price):
    if amount <= 0 or price <= 0:
        return False, "❌ Количество и цена должны быть > 0"
    if order_type not in ['buy', 'sell']:
        return False, "❌ Неверный тип"
    if order_type == 'sell':
        if get_balance_crf(user_id) < amount:
            return False, f"❌ Недостаточно CRF. У вас {get_balance_crf(user_id):.2f}"
        add_transaction_crf(user_id, -amount, 'order_freeze', f'Заморозка CRF для ордера')
    else:
        total_cost = amount * price
        commission = total_cost * 0.20
        total_needed = total_cost + commission
        if get_balance_rub(user_id) < total_needed:
            return False, f"❌ Недостаточно ₽. Нужно {total_needed:.2f} (включая комиссию 20%)"
        add_transaction_rub(user_id, -total_needed, 'order_freeze_rub', f'Заморозка ₽ для ордера покупки CRF (включая комиссию)')
    c = get_cursor()
    c.execute('''
    INSERT INTO crf_orders (user_id, order_type, amount, price)
    VALUES (?, ?, ?, ?)
    ''', (user_id, order_type, amount, price))
    db.commit()
    order_id = c.lastrowid
    match_orders(order_id)
    return True, f"✅ Ордер #{order_id} создан!"

def match_orders(new_order_id):
    c = get_cursor()
    c.execute('SELECT * FROM crf_orders WHERE id = ?', (new_order_id,))
    new_order = c.fetchone()
    if not new_order or new_order['status'] != 'active':
        return
    opposite_type = 'buy' if new_order['order_type'] == 'sell' else 'sell'
    c.execute('''
    SELECT * FROM crf_orders
    WHERE order_type = ? AND status = 'active'
    ORDER BY price ASC
    ''', (opposite_type,))
    matches = c.fetchall()
    for match in matches:
        if new_order['order_type'] == 'sell' and match['price'] >= new_order['price']:
            trade_price = (new_order['price'] + match['price']) / 2
            trade_amount = min(new_order['amount'], match['amount'])
        if trade_amount <= 0:
            continue
            seller_id = new_order['user_id'] if new_order['order_type'] == 'sell' else match['user_id']
            buyer_id = match['user_id'] if match['order_type'] == 'buy' else new_order['user_id']
            commission_rate = get_commission_rate(seller_id)
            total_rub = trade_amount * trade_price
            commission_seller = total_rub * commission_rate
            seller_rub = total_rub - commission_seller
            commission_buy = total_rub * 0.20
            add_transaction_crf(buyer_id, trade_amount, 'trade_buy', f'Покупка CRF по цене {trade_price:.4f} ₽')
            add_transaction_rub(seller_id, seller_rub, 'trade_sell', f'Продажа CRF по цене {trade_price:.4f} ₽ (комиссия {commission_rate*100:.1f}%)')
            add_transaction_rub(0, commission_buy, 'commission_buy', f'Комиссия покупателя при сделке {new_order_id}')
            add_transaction_rub(0, commission_seller, 'commission_seller', f'Комиссия продавца при сделке {new_order_id}')
            c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_market_rub"', (commission_buy + commission_seller,))
        db.commit()
        c.execute('''
        UPDATE crf_orders SET amount = amount - ?, status = CASE WHEN amount - ? <= 0 THEN 'completed' ELSE 'active' END,
        completed_at = CASE WHEN amount - ? <= 0 THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE id = ?
        ''', (trade_amount, trade_amount, trade_amount, new_order['id']))
        c.execute('''
        UPDATE crf_orders SET amount = amount - ?, status = CASE WHEN amount - ? <= 0 THEN 'completed' ELSE 'active' END,
        completed_at = CASE WHEN amount - ? <= 0 THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE id = ?
        ''', (trade_amount, trade_amount, trade_amount, match['id']))
        c.execute('''
        INSERT INTO crf_trades (buy_order_id, sell_order_id, amount, price)
        VALUES (?, ?, ?, ?)
        ''', (buyer_id, seller_id, trade_amount, trade_price))
        db.commit()
        safe_send(buyer_id, f"💹 Сделка совершена! Вы купили {trade_amount:.2f} CRF по {trade_price:.4f} ₽ (комиссия покупателя 20% учтена)")
        safe_send(seller_id, f"💹 Сделка совершена! Вы продали {trade_amount:.2f} CRF по {trade_price:.4f} ₽ (комиссия {commission_rate*100:.1f}%, получено {seller_rub:.2f} ₽)")
        c.execute('SELECT * FROM crf_orders WHERE id = ?', (new_order['id'],))
        updated = c.fetchone()
        if updated and updated['status'] == 'active':
            match_orders(new_order['id'])
            break

def cancel_order(user_id, order_id):
    c = get_cursor()
    c.execute('SELECT * FROM crf_orders WHERE id = ? AND user_id = ? AND status = "active"', (order_id, user_id))
    order = c.fetchone()
    if not order:
        return False, "❌ Ордер не найден или уже завершён."
    if order['order_type'] == 'sell':
        add_transaction_crf(user_id, order['amount'], 'order_unfreeze', f'Разморозка CRF при отмене ордера #{order_id}')
    else:
        total = order['amount'] * order['price']
        total_with_commission = total * 1.20
        add_transaction_rub(user_id, total_with_commission, 'order_unfreeze_rub', f'Разморозка ₽ при отмене ордера #{order_id}')
        c.execute('UPDATE crf_orders SET status = "cancelled" WHERE id = ?', (order_id,))
        db.commit()
        return True, f"✅ Ордер #{order_id} отменён."

    # ============================================================
    # 5. ИНВЕСТИЦИИ И СТЕЙКИНГ (без изменений)
    # ============================================================
def create_investment_crf(user_id, amount, days):
    rate = CONFIG.get('investment_rates', {}).get(str(days), 0.05)
    if is_vip(user_id):
        rate += 0.05
        if amount < CONFIG.get('investment_min', 10):
            return False, f"❌ Минимальная сумма: {CONFIG.get('investment_min', 10)} CRF"
    commission = apply_crf_commission(user_id, amount)
    if commission < 0:
        return False, f"❌ Недостаточно CRF. Нужно {amount + amount*0.20:.2f} (включая комиссию 20%)"
    add_transaction_crf(user_id, -amount, 'invest_start', f'Инвестиция {amount} CRF на {days} дней')
    end_date = (datetime.now() + timedelta(days=days)).isoformat()
    profit = amount * rate
    c = get_cursor()
    c.execute('''
    INSERT INTO investments (user_id, amount, term_days, end_date, profit, currency)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, days, end_date, profit, 'crf'))
    db.commit()
    return True, f"✅ Инвестиция открыта! {amount} CRF на {days} дней. Прибыль: {profit:.2f} CRF ({rate*100:.0f}%)"

def check_investments():
    c = get_cursor()
    now = datetime.now().isoformat()
    c.execute('SELECT * FROM investments WHERE is_active = 1 AND end_date <= ?', (now,))
    invs = c.fetchall()
    for inv in invs:
        user_id = inv['user_id']
        amount = inv['amount']
        profit = inv['profit']
        total = amount + profit
        if inv['currency'] == 'crf':
            add_transaction_crf(user_id, total, 'invest_finish', f'Инвестиция #{inv["id"]} завершена, прибыль {profit:.2f} CRF')
        else:
            add_transaction_rub(user_id, total, 'invest_finish_rub', f'Инвестиция #{inv["id"]} завершена, прибыль {profit:.2f} ₽')
            c.execute('UPDATE investments SET is_active = 0 WHERE id = ?', (inv['id'],))
            safe_send(user_id, f"📈 Инвестиция #{inv['id']} завершена! Получено {total:.2f} {inv['currency'].upper()}")
        db.commit()

def investment_scheduler():
    while True:
        time.sleep(3600)
        check_investments()

        threading.Thread(target=investment_scheduler, daemon=True).start()

def stake_crf(user_id, amount, days):
    if days not in [7,14,30]:
        return False, "❌ Доступные сроки: 7, 14, 30 дней"
    if amount < 1:
        return False, "❌ Минимальная сумма: 1 CRF"
    commission = apply_crf_commission(user_id, amount)
    if commission < 0:
        return False, f"❌ Недостаточно CRF. Нужно {amount + amount*0.20:.2f} (включая комиссию 20%)"
    rate = CONFIG.get('crf_staking_rates', {}).get(str(days), 0.10)
    add_transaction_crf(user_id, -amount, 'stake_start', f'Стейкинг {amount} CRF на {days} дней')
    end_date = (datetime.now() + timedelta(days=days)).isoformat()
    profit = amount * rate
    c = get_cursor()
    c.execute('''
    INSERT INTO crf_stakes (user_id, amount, term_days, end_date, profit)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, days, end_date, profit))
    db.commit()
    return True, f"✅ Стейкинг открыт! {amount} CRF на {days} дней. Прибыль: {profit:.2f} CRF ({rate*100:.0f}%)"

def check_stakes():
    c = get_cursor()
    now = datetime.now().isoformat()
    c.execute('SELECT * FROM crf_stakes WHERE is_active = 1 AND end_date <= ?', (now,))
    stakes = c.fetchall()
    for stake in stakes:
        user_id = stake['user_id']
        amount = stake['amount']
        profit = stake['profit']
        total = amount + profit
        add_transaction_crf(user_id, total, 'stake_finish', f'Стейкинг #{stake["id"]} завершён, прибыль {profit:.2f} CRF')
        c.execute('UPDATE crf_stakes SET is_active = 0 WHERE id = ?', (stake['id'],))
        safe_send(user_id, f"✅ Стейкинг завершён! Получено {total:.2f} CRF")
        db.commit()

def staking_scheduler():
    while True:
        time.sleep(3600)
        check_stakes()

        threading.Thread(target=staking_scheduler, daemon=True).start()

        # ============================================================
        # 6. СЕЗОНЫ (без изменений)
        # ============================================================
def get_active_season():
    c = get_cursor()
    c.execute('SELECT * FROM seasons WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
    return c.fetchone()

def create_season(name, prize_pool):
    c = get_cursor()
    now = datetime.now()
    end_date = now + timedelta(days=CONFIG.get('season_duration_days', 30))
    c.execute('''
    INSERT INTO seasons (name, start_date, end_date, is_active, prize_pool)
    VALUES (?, ?, ?, ?, ?)
    ''', (name, now.isoformat(), end_date.isoformat(), 1, prize_pool))
    db.commit()
    return c.lastrowid

def finish_season(season_id):
    c = get_cursor()
    c.execute('SELECT * FROM seasons WHERE id = ? AND is_active = 1', (season_id,))
    season = c.fetchone()
    if not season:
        return False, "❌ Сезон не найден или уже завершён."
    start = season['start_date']
    end = season['end_date'] or datetime.now().isoformat()
    c.execute('''
    SELECT winner_id, COUNT(*) as wins
    FROM duels
    WHERE status = 'finished' AND winner_id != -1
    AND updated_at >= ? AND updated_at <= ?
    GROUP BY winner_id
    ORDER BY wins DESC
    LIMIT 3
    ''', (start, end))
    winners = c.fetchall()
    prize_pool = season['prize_pool'] or 0
    shares = [0.5, 0.3, 0.2]
    for i, row in enumerate(winners):
        if i >= len(shares):
            break
            reward = prize_pool * shares[i]
            user_id = row['winner_id']
            add_transaction_rub(user_id, reward, 'season_prize', f'Приз сезона {season["name"]} – место {i+1}')
            c.execute('INSERT INTO season_winners (season_id, user_id, place, reward) VALUES (?, ?, ?, ?)',
            (season_id, user_id, i+1, reward))
            safe_send(user_id, f"🏆 Вы заняли {i+1} место в сезоне {season['name']} и получили {reward:.2f} ₽!")
            c.execute('UPDATE seasons SET is_active = 0 WHERE id = ?', (season_id,))
        db.commit()
        return True, f"✅ Сезон {season['name']} завершён! Награды розданы."

def get_season_stats():
    season = get_active_season()
    if not season:
        return None
    c = get_cursor()
    start = season['start_date']
    end = season['end_date'] or datetime.now().isoformat()
    c.execute('SELECT COUNT(*) FROM duels WHERE status = "finished" AND updated_at >= ? AND updated_at <= ?', (start, end))
    total_duels = c.fetchone()[0] or 0
    c.execute('''
    SELECT winner_id, COUNT(*) as wins
    FROM duels
    WHERE status = 'finished' AND winner_id != -1
    AND updated_at >= ? AND updated_at <= ?
    GROUP BY winner_id
    ORDER BY wins DESC
    LIMIT 5
    ''', (start, end))
    top_winners = c.fetchall()
    return {'season': season, 'total_duels': total_duels, 'top_winners': top_winners}

    # ============================================================
    # 7. ДУЭЛИ (с обновлением статистики комиссии 8%)
    # ============================================================
def check_duel_access(user_id):
    level, _ = get_user_level(user_id)
    min_level = CONFIG.get('duel_min_level', 2)
    if level < min_level:
        return False, f"❌ Дуэли доступны с {min_level} уровня."
    blocked_until = get_field(user_id, 'duel_blocked_until', None)
    if blocked_until:
        try:
            block_time = datetime.fromisoformat(blocked_until)
            if datetime.now() < block_time:
                remaining = (block_time - datetime.now()).seconds // 60
                return False, f"⛔ Заблокирован до {block_time.strftime('%H:%M')} (осталось {remaining} мин)"
        except:
            pass
    return True, ""

def check_duel_limit(user_id):
    if is_vip(user_id):
        return True, ""
    level, _ = get_user_level(user_id)
    limit = get_level_bonuses(level)['duel_limit']
    today = datetime.now().date().isoformat()
    c = get_cursor()
    c.execute('''
    SELECT COUNT(*) FROM duels WHERE status = 'finished' AND (creator_id = ? OR opponent_id = ?) AND date(updated_at) = ?
    ''', (user_id, user_id, today))
    count = c.fetchone()[0] or 0
    if count >= limit:
        return False, f"❌ Лимит дуэлей на сегодня ({limit}) исчерпан."
    return True, ""

def create_duel(user_id, amount, mode='classic'):
    access, msg = check_duel_access(user_id)
    if not access:
        return False, msg
    limit_ok, limit_msg = check_duel_limit(user_id)
    if not limit_ok:
        return False, limit_msg
    if amount < 1:
        return False, "❌ Минимальная ставка 1 ₽"
    if get_balance_rub(user_id) < amount:
        return False, f"❌ Недостаточно средств. Нужно {amount:.2f} ₽"
    add_transaction_rub(user_id, -amount, 'duel_hold', f'Создание дуэли')
    c = get_cursor()
    c.execute('''
    INSERT INTO duels (creator_id, amount, mode, status, elo_creator)
    VALUES (?, ?, ?, 'waiting', (SELECT elo_rating FROM users WHERE chatId = ?))
    ''', (user_id, amount, mode, user_id))
    db.commit()
    duel_id = c.lastrowid
    return True, f"✅ Дуэль #{duel_id} создана! Ожидайте соперника."

def resolve_classic_duel(duel_id):
    c = get_cursor()
    c.execute('SELECT * FROM duels WHERE id = ? AND status = "active"', (duel_id,))
    duel = c.fetchone()
    if not duel:
        return False, "❌ Дуэль не активна."
    creator, opponent, amount = duel['creator_id'], duel['opponent_id'], duel['amount']
    total = amount * 2
    commission = total * CONFIG.get('duel_commission', 8.0) / 100.0
    prize = total - commission
    winner = random.choice([creator, opponent])
    loser = opponent if winner == creator else creator
    add_transaction_rub(winner, prize, 'duel_win', f'Победа в дуэли #{duel_id}')
    c.execute('INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
    (0, commission, 'commission', f'Комиссия дуэли #{duel_id}'))
    # Обновляем статистику комиссий дуэлей
    c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_duel_rub"', (commission,))
    db.commit()
    elo_w = get_field(winner, 'elo_rating', 1200)
    elo_l = get_field(loser, 'elo_rating', 1200)
    k = CONFIG.get('elo_k_factor', 32)
    expected_w = 1 / (1 + 10 ** ((elo_l - elo_w) / 400))
    expected_l = 1 / (1 + 10 ** ((elo_w - elo_l) / 400))
    new_w = int(elo_w + k * (1 - expected_w))
    new_l = int(elo_l + k * (0 - expected_l))
    update_field(winner, 'elo_rating', new_w)
    update_field(loser, 'elo_rating', new_l)
    c.execute('UPDATE duels SET status = "finished", winner_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
    (winner, duel_id))
    db.commit()
    add_exp(winner, CONFIG.get('exp_per_duel_win', 5))
    add_exp(loser, 1)
    try:
        update_task_progress(winner, 'duel_wins')
        update_task_progress(winner, 'duel_any')
        update_task_progress(loser, 'duel_any')
    except Exception as e:
        print(f"Ошибка обновления заданий в дуэли: {e}")
        if is_vip(winner) and random.random() < 0.15:
            bonus_crf = round(random.uniform(0.10, 0.30), 2)
            add_transaction_crf(winner, bonus_crf, 'vip_duel_bonus', f'VIP бонус за победу в дуэли')
            safe_send(winner, f"👑 VIP бонус! Вы получили {bonus_crf:.2f} CRF за победу!")
            win_rank, _ = get_rank(new_w)
            lose_rank, _ = get_rank(new_l)
            safe_send(winner, f"🎉 ПОБЕДА!\n\n💰 Выигрыш: {prize:.2f} ₽\n⭐ Рейтинг Elo: {elo_w} → {new_w} ({win_rank})\n🏆 Отлично сражались!")
            safe_send(loser, f"😔 ПОРАЖЕНИЕ\n\n⭐ Рейтинг Elo: {elo_l} → {new_l} ({lose_rank})\n💪 В следующий раз повезёт!")
            return True, f"✅ Дуэль #{duel_id} завершена, победитель {winner}"

def resolve_rps_duel(duel_id):
    c = get_cursor()
    c.execute('SELECT * FROM duels WHERE id = ? AND status = "active"', (duel_id,))
    duel = c.fetchone()
    if not duel:
        return False, "❌ Дуэль не активна."
    creator, opponent, amount = duel['creator_id'], duel['opponent_id'], duel['amount']
    c_choice, o_choice = duel['creator_choice'], duel['opponent_choice']
    if not c_choice or not o_choice:
        return False, "❌ Выборы не сделаны."
    rules = {'rock': 'scissors', 'scissors': 'paper', 'paper': 'rock'}
    total = amount * 2
    commission = total * CONFIG.get('duel_commission', 8.0) / 100.0
    prize = total - commission
    if c_choice == o_choice:
        add_transaction_rub(creator, amount, 'duel_hold', 'Возврат (ничья)')
        add_transaction_rub(opponent, amount, 'duel_hold', 'Возврат (ничья)')
        winner = None
        msg = "🤝 Ничья! Ставки возвращены."
    elif rules[c_choice] == o_choice:
        winner, loser = creator, opponent
        add_transaction_rub(winner, prize, 'duel_win', f'Победа в дуэли #{duel_id}')
        c.execute('INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
        (0, commission, 'commission', f'Комиссия дуэли #{duel_id}'))
        c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_duel_rub"', (commission,))
        db.commit()
        elo_w = get_field(winner, 'elo_rating', 1200)
        elo_l = get_field(loser, 'elo_rating', 1200)
        k = CONFIG.get('elo_k_factor', 32)
        expected_w = 1 / (1 + 10 ** ((elo_l - elo_w) / 400))
        expected_l = 1 / (1 + 10 ** ((elo_w - elo_l) / 400))
        new_w = int(elo_w + k * (1 - expected_w))
        new_l = int(elo_l + k * (0 - expected_l))
        update_field(winner, 'elo_rating', new_w)
        update_field(loser, 'elo_rating', new_l)
        add_exp(winner, CONFIG.get('exp_per_duel_win', 5))
        add_exp(loser, 1)
        try:
            update_task_progress(winner, 'duel_wins')
            update_task_progress(winner, 'duel_any')
            update_task_progress(loser, 'duel_any')
        except Exception as e:
            print(f"Ошибка обновления заданий в RPS дуэли: {e}")
        if is_vip(winner) and random.random() < 0.15:
            bonus_crf = round(random.uniform(0.10, 0.30), 2)
            add_transaction_crf(winner, bonus_crf, 'vip_duel_bonus', f'VIP бонус за победу в дуэли')
            safe_send(winner, f"👑 VIP бонус! Вы получили {bonus_crf:.2f} CRF за победу!")
            win_rank, _ = get_rank(new_w)
            lose_rank, _ = get_rank(new_l)
            safe_send(winner, f"🎉 ПОБЕДА (RPS)!\n\n💰 Выигрыш: {prize:.2f} ₽\n⭐ Рейтинг Elo: {elo_w} → {new_w} ({win_rank})")
            safe_send(loser, f"😔 ПОРАЖЕНИЕ (RPS)\n\n⭐ Рейтинг Elo: {elo_l} → {new_l} ({lose_rank})")
            msg = f"🎉 Победитель: {winner}"
        else:
            winner, loser = opponent, creator
            add_transaction_rub(winner, prize, 'duel_win', f'Победа в дуэли #{duel_id}')
            c.execute('INSERT INTO transactions (user_id, amount, type, description) VALUES (?,?,?,?)',
            (0, commission, 'commission', f'Комиссия дуэли #{duel_id}'))
            c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_duel_rub"', (commission,))
        db.commit()
        elo_w = get_field(winner, 'elo_rating', 1200)
        elo_l = get_field(loser, 'elo_rating', 1200)
        k = CONFIG.get('elo_k_factor', 32)
        expected_w = 1 / (1 + 10 ** ((elo_l - elo_w) / 400))
        expected_l = 1 / (1 + 10 ** ((elo_w - elo_l) / 400))
        new_w = int(elo_w + k * (1 - expected_w))
        new_l = int(elo_l + k * (0 - expected_l))
        update_field(winner, 'elo_rating', new_w)
        update_field(loser, 'elo_rating', new_l)
        add_exp(winner, CONFIG.get('exp_per_duel_win', 5))
        add_exp(loser, 1)
        try:
            update_task_progress(winner, 'duel_wins')
            update_task_progress(winner, 'duel_any')
            update_task_progress(loser, 'duel_any')
        except Exception as e:
            print(f"Ошибка обновления заданий в RPS дуэли: {e}")
        if is_vip(winner) and random.random() < 0.15:
            bonus_crf = round(random.uniform(0.10, 0.30), 2)
            add_transaction_crf(winner, bonus_crf, 'vip_duel_bonus', f'VIP бонус за победу в дуэли')
            safe_send(winner, f"👑 VIP бонус! Вы получили {bonus_crf:.2f} CRF за победу!")
            win_rank, _ = get_rank(new_w)
            lose_rank, _ = get_rank(new_l)
            safe_send(winner, f"🎉 ПОБЕДА (RPS)!\n\n💰 Выигрыш: {prize:.2f} ₽\n⭐ Рейтинг Elo: {elo_w} → {new_w} ({win_rank})")
            safe_send(loser, f"😔 ПОРАЖЕНИЕ (RPS)\n\n⭐ Рейтинг Elo: {elo_l} → {new_l} ({lose_rank})")
            msg = f"🎉 Победитель: {winner}"
            c.execute('UPDATE duels SET status = "finished", winner_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (winner or -1, duel_id))
        db.commit()
        return True, msg

def get_active_duels():
    c = get_cursor()
    c.execute('SELECT * FROM duels WHERE status = "waiting" ORDER BY created_at')
    return c.fetchall()

def get_user_duels(user_id):
    c = get_cursor()
    c.execute('SELECT * FROM duels WHERE creator_id = ? OR opponent_id = ? ORDER BY created_at DESC', (user_id, user_id))
    return c.fetchall()

def get_duel(duel_id):
    c = get_cursor()
    c.execute('SELECT * FROM duels WHERE id = ?', (duel_id,))
    return c.fetchone()

def set_rps_choice(user_id, duel_id, choice):
    c = get_cursor()
    duel = get_duel(duel_id)
    if not duel or duel['status'] != 'active':
        return False, "❌ Дуэль не активна."
    if user_id not in (duel['creator_id'], duel['opponent_id']):
        return False, "❌ Вы не участник."
    if user_id == duel['creator_id']:
        if duel['creator_choice']:
            return False, "❌ Вы уже сделали выбор."
        c.execute('UPDATE duels SET creator_choice = ? WHERE id = ?', (choice, duel_id))
    else:
        if duel['opponent_choice']:
            return False, "❌ Вы уже сделали выбор."
        c.execute('UPDATE duels SET opponent_choice = ? WHERE id = ?', (choice, duel_id))
    db.commit()
    duel = get_duel(duel_id)
    if duel['creator_choice'] and duel['opponent_choice']:
        return resolve_rps_duel(duel_id)
    return True, "✅ Выбор сохранён."

# ============================================================
# 8. ЕЖЕДНЕВНЫЕ ЗАДАНИЯ (С КНОПКОЙ "ЗАБРАТЬ")
# ============================================================
def generate_daily_tasks():
    c = get_cursor()
    c.execute('DELETE FROM daily_tasks')
    tasks = [
    {'type': 'referrals', 'text': 'Пригласите {target} друзей', 'target_min': 1, 'target_max': 3, 'exp': 10},
    {'type': 'duel_wins', 'text': 'Выиграйте {target} дуэлей', 'target_min': 1, 'target_max': 3, 'exp': 15},
    {'type': 'spins', 'text': 'Крутите колесо {target} раз', 'target_min': 1, 'target_max': 3, 'exp': 8},
    {'type': 'deposit', 'text': 'Пополните баланс на {target} ₽', 'target_min': 50, 'target_max': 200, 'exp': 20},
    {'type': 'withdraw', 'text': 'Выведите {target} ₽', 'target_min': 20, 'target_max': 100, 'exp': 15},
    {'type': 'duel_any', 'text': 'Проведите {target} дуэлей', 'target_min': 2, 'target_max': 5, 'exp': 12},
    ]
    selected = random.sample(tasks, min(CONFIG.get('daily_tasks_count', 3), len(tasks)))
    for t in selected:
        target = random.randint(t['target_min'], t['target_max'])
        text = t['text'].replace('{target}', str(target))
        reward = round(random.uniform(0.1, 1.0), 2)
        c.execute('''
        INSERT INTO daily_tasks (task_text, task_type, target, reward_exp, reward_money)
        VALUES (?, ?, ?, ?, ?)
        ''', (text, t['type'], target, t['exp'], reward))
        db.commit()

def get_daily_tasks(user_id):
    today = datetime.now().date().isoformat()
    c = get_cursor()
    c.execute('SELECT daily_tasks_date FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    if not row or row[0] != today:
        c.execute('SELECT COUNT(*) FROM daily_tasks')
        if c.fetchone()[0] == 0:
            generate_daily_tasks()
            c.execute('DELETE FROM user_daily_progress WHERE user_id = ?', (user_id,))
            c.execute('UPDATE users SET daily_tasks_date = ?, daily_tasks_done = "" WHERE chatId = ?', (today, user_id))
        db.commit()
        c.execute('SELECT * FROM daily_tasks')
        tasks = c.fetchall()
        result = []
        for t in tasks:
            c.execute('SELECT progress, completed, claimed FROM user_daily_progress WHERE user_id = ? AND task_id = ?', (user_id, t['id']))
            prog = c.fetchone()
            progress = prog['progress'] if prog else 0
            completed = prog['completed'] if prog else 0
            claimed = prog['claimed'] if prog else 0
            result.append({
            'id': t['id'],
            'text': t['task_text'],
            'type': t['task_type'],
            'target': t['target'],
            'reward_exp': t['reward_exp'],
            'reward_money': t['reward_money'],
            'progress': progress,
            'completed': completed,
            'claimed': claimed
            })
            return result

def update_task_progress(user_id, task_type, amount=1):
    c = get_cursor()
    today = datetime.now().date().isoformat()
    c.execute('SELECT daily_tasks_date FROM users WHERE chatId = ?', (user_id,))
    row = c.fetchone()
    if not row or row[0] != today:
        return
    c.execute('SELECT id FROM daily_tasks WHERE task_type = ?', (task_type,))
    tasks = c.fetchall()
    for t in tasks:
        task_id = t['id']
        c.execute('SELECT progress, completed, claimed FROM user_daily_progress WHERE user_id = ? AND task_id = ?', (user_id, task_id))
        prog = c.fetchone()
        if prog and prog['completed']:
            continue
            new_progress = (prog['progress'] if prog else 0) + amount
            c.execute('SELECT target, reward_exp, reward_money FROM daily_tasks WHERE id = ?', (task_id,))
            info = c.fetchone()
        if not info:
            continue
        if new_progress >= info['target']:
            completed = 1
            safe_send(user_id, f"✅ Задание выполнено! Нажмите кнопку 'Забрать награду' в списке заданий.")
        else:
            completed = 0
            c.execute('''
            INSERT INTO user_daily_progress (user_id, task_id, progress, completed, claimed)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id, task_id) DO UPDATE SET progress = ?, completed = ?, claimed = 0
            ''', (user_id, task_id, new_progress, completed, new_progress, completed))
        db.commit()

def claim_daily_reward(user_id, task_id):
    c = get_cursor()
    c.execute('SELECT completed, claimed, reward_exp, reward_money, task_text FROM user_daily_progress JOIN daily_tasks ON user_daily_progress.task_id = daily_tasks.id WHERE user_id = ? AND task_id = ?', (user_id, task_id))
    row = c.fetchone()
    if not row:
        return False, "❌ Задание не найдено."
    if not row['completed']:
        return False, "❌ Задание ещё не выполнено."
    if row['claimed']:
        return False, "❌ Награда уже получена."
    add_exp(user_id, row['reward_exp'])
    add_transaction_crf(user_id, row['reward_money'], 'task_daily', f'Ежедневное задание: {row["task_text"]}')
    c.execute('UPDATE user_daily_progress SET claimed = 1 WHERE user_id = ? AND task_id = ?', (user_id, task_id))
    db.commit()
    return True, f"✅ Вы получили {row['reward_money']:.2f} CRF и {row['reward_exp']} опыта!"

    # ============================================================
    # 9. МЕНЮ (ВСЁ В ГЛАВНОМ МЕНЮ – REPLY-КНОПКИ)
    # ============================================================
def main_menu(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.row('👤 Кабинет', '💱 Биржа', '⚔️ Дуэль')
    kb.row('📈 Инвестиции', '📋 Задания', '👑 VIP')
    kb.row('💰 Заработать', '🎁 Бонус', '🎲 Колесо удачи')
    kb.row('📅 Сезон', '📢 Продвижение', '🆘 Поддержка')
    if is_admin(user_id):
        kb.row('👑 Админ-панель')
    elif is_moderator(user_id):
        kb.row('🛡️ Модератор-панель')
        return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('❌ Отменить')
    return kb

def cabinet_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('💸 Вывести ₽', '💳 Пополнить')
    kb.row('📊 История', '🔙 Назад')
    return kb

def exchange_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('🔄 Обменять ₽→CRF', '🔄 Обменять CRF→₽')
    kb.row('📊 История операций', '🔙 Назад')
    return kb

def duel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('🎲 Классическая', '✊ КНБ')
    kb.row('📋 Активные дуэли', '📊 Мои дуэли')
    kb.row('🔙 Назад')
    return kb

def invest_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('📈 Создать инвестицию', '💎 Стейкинг')
    kb.row('📊 Мои инвестиции', '📊 Мои стейки')
    kb.row('🔙 Назад')
    return kb

def staking_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('7 дней (10%)', '14 дней (15%)')
    kb.row('30 дней (20%)', '🔙 Назад')
    return kb

def vip_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('👑 Купить VIP за 100 ₽', '🔙 Назад')
    return kb

def referral_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('📤 Поделиться ссылкой', '🔙 Назад')
    return kb

def promo_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row('📨 Рассылка', '📢 Реклама канала')
    kb.row('🔙 Назад')
    return kb

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(
    InlineKeyboardButton('📛 Заявки на вывод', callback_data='admin_withdraws'),
    InlineKeyboardButton('📥 Заявки на пополнение', callback_data='admin_deposits')
    )
    kb.row(
    InlineKeyboardButton('📟 Рассылка', callback_data='admin_broadcast'),
    InlineKeyboardButton('🏦 Реквизиты пополнения', callback_data='admin_replenish_settings')
    )
    kb.row(
    InlineKeyboardButton('💰 Баланс ₽', callback_data='admin_balance_rub'),
    InlineKeyboardButton('💎 Баланс CRF', callback_data='admin_balance_crf')
    )
    kb.row(
    InlineKeyboardButton('📈 Курс CRF', callback_data='admin_crf_rate'),
    InlineKeyboardButton('📋 Запросы модераторов', callback_data='admin_requests')
    )
    kb.row(
    InlineKeyboardButton('📊 Транзакции', callback_data='admin_transactions'),
    InlineKeyboardButton('📈 Выдать уровень', callback_data='admin_give_level')
    )
    kb.row(
    InlineKeyboardButton('📊 Изменить реф. уровень', callback_data='admin_change_refs'),
    InlineKeyboardButton('🔄 Обновить', callback_data='admin_refresh')
    )
    kb.row(
    InlineKeyboardButton('📊 Детальная статистика', callback_data='admin_stats'),
    InlineKeyboardButton('🗑️ Очистить статистику', callback_data='admin_clear_stats')
    )
    kb.row(
    InlineKeyboardButton('📅 Управление сезонами', callback_data='admin_seasons'),
    InlineKeyboardButton('📝 Создать задание с подпиской', callback_data='admin_task_subscribe')
    )
    kb.row(
    InlineKeyboardButton('📋 Список заданий (с управлением)', callback_data='admin_tasks_list')
    )
    return kb

def moderator_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(
    InlineKeyboardButton('🚫 Заблокировать', callback_data='mod_ban'),
    InlineKeyboardButton('✅ Разблокировать', callback_data='mod_unban')
    )
    kb.row(
    InlineKeyboardButton('💰 Изменить ₽', callback_data='mod_balance_rub'),
    InlineKeyboardButton('💎 Изменить CRF', callback_data='mod_balance_crf')
    )
    kb.row(
    InlineKeyboardButton('📈 Изменить уровень', callback_data='mod_level'),
    InlineKeyboardButton('👑 Выдать VIP', callback_data='mod_vip')
    )
    kb.row(
    InlineKeyboardButton('📛 Отменить вывод', callback_data='mod_cancel_withdraw')
    )
    return kb

    # ============================================================
    # 10. ОБРАБОТЧИКИ ТЕКСТОВЫХ КНОПОК МЕНЮ (ВСЕ ОТПРАВЛЯЮТ НОВЫЕ СООБЩЕНИЯ)
    # ============================================================
@bot.message_handler(func=lambda m: m.text == '👤 Кабинет')
def cabinet_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл кабинет")
    user = get_user(user_id)
    if not user:
        safe_send(m.chat.id, "❌ Ошибка")
        return
    rub = get_balance_rub(user_id)
    crf = get_balance_crf(user_id)
    level, exp = get_user_level(user_id)
    required = get_level_config(level)
    progress = int((exp / required) * 100) if required else 0
    elo = get_field(user_id, 'elo_rating', 1200)
    rank, emoji = get_rank(elo)
    ref_level = get_field(user_id, 'ref_level', 1)
    bonuses = get_level_bonuses(level)
    vip = "👑 Да" if is_vip(user_id) else "❌ Нет"
    if is_vip(user_id):
        duel_limit_display = "🚫"
    else:
        duel_limit_display = f"{bonuses['duel_limit']}"
        c = get_cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE referer = ?', (user_id,))
        refs = c.fetchone()[0] or 0

        text = f"""👤 ВАШ КАБИНЕТ

        📋 Информация:
        • Имя: {user['firstName'] or 'Пользователь'}
        • ID: {user_id}
        • Уровень: {level} (опыт: {exp}/{required}, {progress}%)
        • Реферальный уровень: {ref_level}
        • Рейтинг Elo: {elo} ({emoji} {rank})
        • VIP: {vip}

        💳 Финансы:
        • Баланс: {rub:.2f} ₽
        • Баланс CRF: {crf:.2f}

        🎯 Доступные функции:
        • Лимит дуэлей: {duel_limit_display}
        • Комиссия вывода: {bonuses['withdraw_fee']:.1f}%

        👥 Рефералов: {refs}
        ━━━━━━━━━━━━━━━━━━━━━
        💡 Используйте кнопки ниже"""
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=cabinet_kb())

@bot.message_handler(func=lambda m: m.text == '💱 Биржа')
def exchange_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл биржу")
    rate = get_crf_rate()
    text = f"""💱 БИРЖА CRF

    Текущий курс: 1 CRF = {rate:.4f} ₽

    Здесь вы можете обменивать валюты.
    Комиссия при обмене: 10%

    Выберите действие:"""
    safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=exchange_kb())

@bot.message_handler(func=lambda m: m.text == '📊 История операций')
def exchange_history_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    rub_tx = c.fetchall()
    c.execute('SELECT * FROM crf_transactions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    crf_tx = c.fetchall()

    total_rub_in = 0
    total_rub_out = 0
    total_crf_in = 0
    total_crf_out = 0

    text = "📊 ИСТОРИЯ ОПЕРАЦИЙ (все)\n\n"

    if rub_tx:
        text += "💰 РУБЛИ (₽):\n"
        for t in rub_tx:
            amount = t['amount']
        if amount > 0:
            total_rub_in += amount
            sign = "+"
        else:
            total_rub_out += abs(amount)
            sign = ""
            text += f"{t['created_at'][:10]} {t['type']}: {sign}{amount:.2f} ₽ – {t['description']}\n"
            text += "\n"
        if crf_tx:
            text += "💎 CRF:\n"
        for t in crf_tx:
            amount = t['amount']
        if amount > 0:
            total_crf_in += amount
            sign = "+"
        else:
            total_crf_out += abs(amount)
            sign = ""
            text += f"{t['created_at'][:10]} {t['type']}: {sign}{amount:.2f} CRF – {t['description']}\n"
            text += "\n"

        if not rub_tx and not crf_tx:
            text += "Нет операций.\n"
        else:
            text += "📊 СВОДКА:\n"
            text += f"💰 Всего получено ₽: {total_rub_in:.2f}\n"
            text += f"💰 Всего потрачено ₽: {total_rub_out:.2f}\n"
            text += f"💎 Всего получено CRF: {total_crf_in:.2f}\n"
            text += f"💎 Всего потрачено CRF: {total_crf_out:.2f}\n"

            safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=exchange_kb())

@bot.message_handler(func=lambda m: m.text == '🔄 Обменять ₽→CRF')
def exchange_rub_to_crf_btn(m):
    user_id = m.from_user.id
    rate = get_crf_rate()
    safe_send(m.chat.id, f"🔄 Введите сумму в ₽ для обмена на CRF. Курс: 1 CRF = {rate:.4f} ₽ (комиссия 10%)", reply_markup=cancel_kb())
    user_states[user_id] = {'state': 'exchange_rub_to_crf'}

@bot.message_handler(func=lambda m: m.text == '🔄 Обменять CRF→₽')
def exchange_crf_to_rub_btn(m):
    user_id = m.from_user.id
    rate = get_crf_rate()
    safe_send(m.chat.id, f"🔄 Введите сумму в CRF для обмена на ₽. Курс: 1 CRF = {rate:.4f} ₽ (комиссия 10%)", reply_markup=cancel_kb())
    user_states[user_id] = {'state': 'exchange_crf_to_rub'}

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_btn(m):
    user_id = m.from_user.id
    safe_send(m.chat.id, "Главное меню", reply_markup=main_menu(user_id))

# -------- ДУЭЛИ --------
@bot.message_handler(func=lambda m: m.text == '⚔️ Дуэль')
def duel_menu_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл дуэли")
    if get_field(user_id, 'is_banned', 0):
        return
    if not get_field(user_id, 'is_verified', 0):
        safe_send(m.chat.id, "❌ Пройдите верификацию.")
        return
    safe_send(m.chat.id, "⚔️ ДУЭЛИ\n\nВыберите режим или действие:", reply_markup=duel_kb())

@bot.message_handler(func=lambda m: m.text == '🎲 Классическая')
def duel_classic_btn(m):
    user_id = m.from_user.id
    user_states[user_id] = {'state': 'duel_amount', 'mode': 'classic'}
    safe_send(m.chat.id, "💰 Введите сумму ставки (в ₽):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == '✊ КНБ')
def duel_rps_btn(m):
    user_id = m.from_user.id
    user_states[user_id] = {'state': 'duel_amount', 'mode': 'rps'}
    safe_send(m.chat.id, "💰 Введите сумму ставки (в ₽):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == '📋 Активные дуэли')
def duel_list_btn(m):
    user_id = m.from_user.id
    duels = get_active_duels()
    if not duels:
        safe_send(m.chat.id, "📭 Нет активных дуэлей.")
        return
    text = "⚔️ АКТИВНЫЕ ДУЭЛИ\n\n"
    kb = InlineKeyboardMarkup(row_width=1)
    for d in duels:
        creator = get_user(d['creator_id'])
        name = creator['firstName'] if creator else str(d['creator_id'])
        text += f"#{d['id']} | {d['mode'].capitalize()} | {name} | {d['amount']:.2f} ₽\n"
        kb.add(InlineKeyboardButton(f'Принять #{d["id"]}', callback_data=f'duel_accept_{d["id"]}'))
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='duel_back_inline'))
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == '📊 Мои дуэли')
def duel_my_btn(m):
    user_id = m.from_user.id
    duels = get_user_duels(user_id)
    if not duels:
        safe_send(m.chat.id, "📭 У вас нет дуэлей.")
        return
    text = "📊 МОИ ДУЭЛИ\n\n"
    for d in duels:
        status = {'waiting':'⏳','active':'⚔️','finished':'✅'}.get(d['status'], '❓')
        creator = get_user(d['creator_id'])
        cname = creator['firstName'] if creator else str(d['creator_id'])
        opponent = "ожидает"
        if d['opponent_id'] != -1:
            opp = get_user(d['opponent_id'])
            opponent = opp['firstName'] if opp else str(d['opponent_id'])
            text += f"{status} #{d['id']} | {d['mode'].capitalize()}\n"
            text += f"Создатель: {cname}, Соперник: {opponent}\n"
            text += f"Ставка: {d['amount']:.2f} ₽\n"
        if d['winner_id'] != -1:
            win = get_user(d['winner_id'])
            text += f"Победитель: {win['firstName'] if win else str(d['winner_id'])}\n"
            text += "━━━━━━━━━━━━━━━━\n"
            safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=duel_kb())

# -------- ИНВЕСТИЦИИ --------
@bot.message_handler(func=lambda m: m.text == '📈 Инвестиции')
def invest_menu_btn(m):
    log_action(m.from_user.id, "Открыл инвестиции")
    safe_send(m.chat.id, "📈 ИНВЕСТИЦИИ И СТЕЙКИНГ\n\nВкладывайте CRF и получайте прибыль.\nКомиссия при вкладе: 20%.", reply_markup=invest_kb())

@bot.message_handler(func=lambda m: m.text == '📈 Создать инвестицию')
def invest_create_btn(m):
    user_id = m.from_user.id
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.row('1 день (5%)', '3 дня (10%)', '7 дней (15%)')
    kb.row('🔙 Назад')
    safe_send(m.chat.id, "📈 Выберите срок инвестиции:", reply_markup=kb)
    user_states[user_id] = {'state': 'invest_choose'}

@bot.message_handler(func=lambda m: m.text in ['1 день (5%)', '3 дня (10%)', '7 дней (15%)'])
def invest_choose_days(m):
    user_id = m.from_user.id
    days = {'1 день (5%)': 1, '3 дня (10%)': 3, '7 дней (15%)': 7}[m.text]
    user_states[user_id] = {'state': 'invest_amount', 'days': days}
    safe_send(m.chat.id, f"📈 Введите сумму CRF для инвестиции на {days} дней (мин. 10, с комиссией 20%):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == '💎 Стейкинг')
def staking_menu_btn(m):
    user_id = m.from_user.id
    safe_send(m.chat.id, "💎 СТЕЙКИНГ CRF\n\nВыберите срок:", reply_markup=staking_kb())

@bot.message_handler(func=lambda m: m.text in ['7 дней (10%)', '14 дней (15%)', '30 дней (20%)'])
def stake_choose_days(m):
    user_id = m.from_user.id
    days = {'7 дней (10%)': 7, '14 дней (15%)': 14, '30 дней (20%)': 30}[m.text]
    user_states[user_id] = {'state': 'stake_amount', 'days': days}
    safe_send(m.chat.id, f"💎 Введите сумму CRF для стейкинга на {days} дней (мин. 1, с комиссией 20%):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == '📊 Мои инвестиции')
def my_investments_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT * FROM investments WHERE user_id = ? AND is_active = 1 ORDER BY end_date ASC', (user_id,))
    invs = c.fetchall()
    if not invs:
        safe_send(m.chat.id, "📭 Нет активных инвестиций.")
        return
    text = "📈 ВАШИ ИНВЕСТИЦИИ\n\n"
    for inv in invs:
        text += f"🔹 {inv['amount']:.2f} {inv['currency'].upper()} на {inv['term_days']} дн., прибыль: {inv['profit']:.2f} {inv['currency'].upper()}, до {datetime.fromisoformat(inv['end_date']).strftime('%d.%m %H:%M')}\n"
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=invest_kb())

@bot.message_handler(func=lambda m: m.text == '📊 Мои стейки')
def my_stakes_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT * FROM crf_stakes WHERE user_id = ? AND is_active = 1 ORDER BY end_date ASC', (user_id,))
    stakes = c.fetchall()
    if not stakes:
        safe_send(m.chat.id, "📭 Нет активных стейков.")
        return
    text = "💎 ВАШИ СТЕЙКИ\n\n"
    for s in stakes:
        text += f"🔹 {s['amount']:.2f} CRF на {s['term_days']} дн., прибыль: {s['profit']:.2f} CRF, до {datetime.fromisoformat(s['end_date']).strftime('%d.%m %H:%M')}\n"
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=invest_kb())

# -------- VIP --------
@bot.message_handler(func=lambda m: m.text == '👑 VIP')
def vip_menu_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл VIP")
    if is_vip(user_id):
        remaining = get_vip_remaining(user_id)
        text = f"""👑 VIP СТАТУС

        VIP активен до: {datetime.fromisoformat(get_field(user_id, 'vip_until')).strftime('%d.%m.%Y %H:%M')}
        Осталось: {format_time_remaining(remaining)}

        Преимущества VIP:
        ✅ Комиссия на рынке – 5% (вместо 20%)
        ✅ Безлимит дуэлей
        ✅ Шанс 15% получить 0.10-0.30 CRF за победу в дуэли
        ✅ Увеличенная доходность инвестиций +5%
        ✅ Удвоенный бонус

        VIP покупается ОДИН РАЗ и действует 30 дней.
        """
    else:
        text = """👑 VIP СТАТУС

        VIP даёт мощные преимущества на 30 дней:

        ✅ Комиссия на рынке – 5% (вместо 20%)
        ✅ Безлимит дуэлей
        ✅ Шанс 15% получить 0.10-0.30 CRF за победу в дуэли
        ✅ Увеличенная доходность инвестиций +5%
        ✅ Удвоенный бонус

        VIP покупается ОДИН РАЗ и действует 30 дней.
        Цена: 100 ₽.

        Нажмите кнопку ниже для покупки:"""
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=vip_kb())

@bot.message_handler(func=lambda m: m.text == '👑 Купить VIP за 100 ₽')
def buy_vip_btn(m):
    user_id = m.from_user.id
    success, msg = buy_vip(user_id)
    safe_send(m.chat.id, msg, reply_markup=vip_kb())

# -------- ЗАРАБОТАТЬ (РЕФЕРАЛКА) --------
@bot.message_handler(func=lambda m: m.text == '💰 Заработать')
def earn_menu_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл реферальную программу")
    ref_level = get_field(user_id, 'ref_level', 1)
    ref_bonus = CONFIG.get('referral_crf', {}).get(str(ref_level), 0.35)
    c = get_cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE referer = ?', (user_id,))
    count = c.fetchone()[0] or 0
    if count >= 50:
        level, emoji = 3, "🥇"
    elif count >= 10:
        level, emoji = 2, "🥈"
    else:
        level, emoji = 1, "🥉"
        text = f"""💰 РЕФЕРАЛЬНАЯ ПРОГРАММА

        {emoji} Уровень: {level}
        👥 Приглашено: {count}
        💎 За каждого реферала вы получаете CRF (зависит от вашего реферального уровня):

        • 1 уровень: 0.35 CRF
        • 2 уровень: 0.70 CRF
        • 3 уровень: 1.15 CRF

        Ваш текущий реферальный уровень: {ref_level}
        Бонус за нового реферала: {ref_bonus:.2f} CRF

        👇 Поделитесь ссылкой и зарабатывайте!"""
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=referral_kb())

@bot.message_handler(func=lambda m: m.text == '📤 Поделиться ссылкой')
def share_ref_link(m):
    user_id = m.from_user.id
    ref_link = f"https://t.me/{botUsername}?start={user_id}"
    safe_send(m.chat.id, f"📤 Ваша реферальная ссылка:\n{ref_link}\n\nОтправьте её друзьям!", reply_markup=referral_kb())

# -------- БОНУС И КОЛЕСО --------
@bot.message_handler(func=lambda m: m.text == '🎁 Бонус')
def bonus_btn_global(m):
    bonus_btn(m)

@bot.message_handler(func=lambda m: m.text == '🎲 Колесо удачи')
def wheel_btn_global(m):
    wheel_btn(m)

# -------- СЕЗОН --------
@bot.message_handler(func=lambda m: m.text == '📅 Сезон')
def season_menu_btn(m):
    log_action(m.from_user.id, "Открыл сезон")
    stats = get_season_stats()
    if not stats:
        safe_send(m.chat.id, "📭 В данный момент нет активного сезона.")
        return
    season = stats['season']
    text = f"📅 СЕЗОН: {season['name']}\n"
    start = datetime.fromisoformat(season['start_date']).strftime('%d.%m.%Y %H:%M')
    end = datetime.fromisoformat(season['end_date']).strftime('%d.%m.%Y %H:%M')
    now = datetime.now()
    end_dt = datetime.fromisoformat(season['end_date'])
    if now < end_dt:
        remaining = end_dt - now
        days = remaining.days
        hours = remaining.seconds // 3600
        text += f"⏳ До конца: {days} дн. {hours} ч.\n"
    else:
        text += "⏳ Сезон завершён!\n"
        text += f"📊 Всего дуэлей: {stats['total_duels']}\n"
        text += f"💰 Призовой фонд: {season['prize_pool']:.2f} ₽\n\n"
        text += "🏆 ТОП ПОБЕДИТЕЛЕЙ СЕЗОНА\n"
        if stats['top_winners']:
            medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
        for i, row in enumerate(stats['top_winners']):
            user = get_user(row['winner_id'])
            name = user['firstName'] if user else str(row['winner_id'])
            text += f"{medals[i] if i < 5 else ''} {name} – {row['wins']} побед\n"
        else:
            text += "Пока нет данных.\n"
            safe_send(m.chat.id, text, parse_mode='HTML')

# -------- ПРОДВИЖЕНИЕ --------
@bot.message_handler(func=lambda m: m.text == '📢 Продвижение')
def promo_menu_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл продвижение")
    safe_send(m.chat.id, "📢 ПРОДВИЖЕНИЕ\n\nВыберите тип продвижения:", reply_markup=promo_kb())

@bot.message_handler(func=lambda m: m.text == '📨 Рассылка')
def promo_mailing_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0] or 0
    user_states[user_id] = {'state': 'promo_mailing_users'}
    safe_send(m.chat.id, f"📨 Введите количество пользователей для рассылки (макс. {total}, 0 – всем):", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == '📢 Реклама канала')
def promo_channel_btn(m):
    user_id = m.from_user.id
    user_states[user_id] = {'state': 'promo_channel_channel'}
    safe_send(m.chat.id, "📢 Введите username канала для рекламы (без @):", reply_markup=cancel_kb())

# -------- ПОДДЕРЖКА --------
@bot.message_handler(func=lambda m: m.text == '🆘 Поддержка')
def support_btn(m):
    user_id = m.from_user.id
    log_action(user_id, "Открыл поддержку")
    safe_send(m.chat.id, "🆘 Напишите ваше сообщение, и мы ответим вам в ближайшее время.", reply_markup=cancel_kb())
    user_states[user_id] = {'state': 'support'}

# -------- АДМИН-ПАНЕЛЬ --------
@bot.message_handler(func=lambda m: m.text == '👑 Админ-панель')
def admin_panel_btn(m):
    if is_admin(m.from_user.id):
        log_action(m.from_user.id, "Открыл админ-панель")
        text = "👑 АДМИН-ПАНЕЛЬ\n\nВыберите действие:"
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=admin_kb())
    else:
        safe_send(m.chat.id, '⛔ Доступ запрещён!')

@bot.message_handler(func=lambda m: m.text == '🛡️ Модератор-панель')
def mod_panel_btn(m):
    if is_moderator(m.from_user.id):
        log_action(m.from_user.id, "Открыл модератор-панель")
        text = "🛡️ МОДЕРАТОР-ПАНЕЛЬ\n\nДействия отправляют запрос администраторам."
        safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=moderator_kb())
    else:
        safe_send(m.chat.id, '⛔ Доступ запрещён!')

# ============================================================
# 11. КОМАНДЫ
# ============================================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    if get_field(user_id, 'is_banned', 0):
        safe_send(message.chat.id, "🚫 Аккаунт заблокирован!")
        return
    user = get_user(user_id)
    if not user:
        c = get_cursor()
        c.execute('INSERT INTO users (chatId, firstName, username) VALUES (?, ?, ?)',
                  (user_id, message.from_user.first_name or '', message.from_user.username or ''))
        db.commit()
        c.execute('INSERT INTO crf_balances (user_id, balance) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING', (user_id,))
        db.commit()
        c.execute('UPDATE stats SET value = value + 1 WHERE key = "total_users"')
        db.commit()
    if not check_subscription(user_id):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('📢 Подписаться', url='https://t.me/COINREF_OFFICIAL'))
        kb.add(InlineKeyboardButton('✅ Я подписался', callback_data='check_sub'))
        safe_send(message.chat.id, CONFIG.get('subscribemsg', '📢 Подпишитесь на каналы!'), reply_markup=kb)
        return
    if not check_extra_subscriptions(user_id):
        kb = InlineKeyboardMarkup()
        c = get_cursor()
        c.execute('SELECT DISTINCT channel FROM promo_subscriptions')
        for row in c.fetchall():
            ch = row['channel']
            kb.add(InlineKeyboardButton(f'📢 Подписаться на {ch}', url=f'https://t.me/{ch}'))
        kb.add(InlineKeyboardButton('✅ Я подписался', callback_data='check_extra_sub'))
        safe_send(message.chat.id, "📢 Для доступа ко всем функциям подпишитесь на рекламные каналы:", reply_markup=kb)
        return
    if not get_field(user_id, 'is_verified', 0):
        code = generate_verification_code()
        update_field(user_id, 'verification_code', code)
        text = f'''🔐 ВЕРИФИКАЦИЯ

Ваш код подтверждения: {code}

Напишите этот код в ответ на это сообщение.
Код действителен 10 минут.'''
        safe_send(message.chat.id, text, parse_mode='HTML', reply_markup=cancel_kb())
        user_states[user_id] = {'state': 'verification', 'code': code, 'time': datetime.now()}
        return
    safe_send(message.chat.id, CONFIG.get('hellomsg', '🌟 Добро пожаловать!'), parse_mode='HTML', reply_markup=main_menu(user_id))

def check_subscription(user_id):
    required = CONFIG.get('requiredChannels', '')
    if not required:
        return True
    for ch in required.split(','):
        ch = clean_channel(ch)
        if ch:
            try:
                m = bot.get_chat_member(f'@{ch}', user_id)
                if m.status in ['left', 'kicked']:
                    return False
            except:
                return False
    return True

def check_extra_subscriptions(user_id):
    c = get_cursor()
    c.execute('SELECT channel FROM promo_subscriptions')
    for row in c.fetchall():
        ch = row['channel']
        try:
            m = bot.get_chat_member(f'@{ch}', user_id)
            if m.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """📚 ПОМОЩЬ ПО БОТУ

    👤 Кабинет – ваш баланс, уровень, история, вывод, пополнение.
    💱 Биржа – курс CRF, обмен валют, история операций.
    ⚔️ Дуэль – сражайтесь за деньги и рейтинг.
    📈 Инвестиции – вкладывайте CRF под процент.
    📋 Задания – ежедневные квесты за CRF и опыт.
    👑 VIP – привилегии на 30 дней.
    💰 Заработать – реферальная программа.
    🎁 Бонус – ежедневный бонус CRF.
    🎲 Колесо удачи – выигрывайте CRF.
    📅 Сезон – соревнование за призы.
    📢 Продвижение – заказ рекламы и рассылок.
    🆘 Поддержка – обратная связь.

    Вся экономика в CRF! Рубли только для дуэлей и вывода.
    """
    safe_send(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu(message.from_user.id))

@bot.message_handler(commands=['level'])
def level_cmd(message):
    user_id = message.from_user.id
    level, exp = get_user_level(user_id)
    required = get_level_config(level)
    progress = int((exp / required) * 100) if required else 0
    bonuses = get_level_bonuses(level)
    vip = "👑 Да" if is_vip(user_id) else "❌ Нет"
    text = f"📈 ВАШ УРОВЕНЬ\n\nУровень: {level}\nОпыт: {exp}/{required} ({progress}%)\nVIP: {vip}\n\nБонус: до {bonuses['bonus_max_crf']:.2f} CRF\nКолесо: до {bonuses['spin_max_crf']:.2f} CRF\nЛимит дуэлей: {bonuses['duel_limit']}"
    safe_send(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu(user_id))

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if is_admin(message.from_user.id):
        admin_panel_btn(message)
    else:
        safe_send(message.chat.id, '⛔ Доступ запрещён!')

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
        safe_send(message.chat.id, '✅ Отменено.', reply_markup=main_menu(user_id))

@bot.message_handler(commands=['reply_ticket'])
def reply_ticket_cmd(message):
    if not is_admin(message.from_user.id):
        safe_send(message.chat.id, '⛔ Доступ запрещён!')
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        safe_send(message.chat.id, '❌ Использование: /reply_ticket <текст ответа>')
        return
    try:
        ticket_id = int(parts[1])
    except:
        safe_send(message.chat.id, '❌ ID тикета должно быть числом')
        return
    reply_text = parts[2]
    c = get_cursor()
    c.execute('SELECT * FROM tickets WHERE id = ? AND status = "open"', (ticket_id,))
    ticket = c.fetchone()
    if not ticket:
        safe_send(message.chat.id, '❌ Тикет не найден или уже закрыт.')
        return
    user_id = ticket['user_id']
    c.execute('UPDATE tickets SET status = "resolved", resolved_at = CURRENT_TIMESTAMP, admin_response = ? WHERE id = ?',
    (reply_text, ticket_id))
    db.commit()
    safe_send(user_id, f"📩 Ответ на ваш тикет #{ticket_id}:\n{reply_text}")
    safe_send(message.chat.id, f"✅ Ответ на тикет #{ticket_id} отправлен пользователю.")
    log_action(message.from_user.id, f"Ответил на тикет #{ticket_id}", f"Текст: {reply_text}")

def get_stat_value(key, default=0):
    c = get_cursor()
    c.execute('SELECT value FROM stats WHERE key = ?', (key,))
    row = c.fetchone()
    if not row:
        return default
    try:
        return row['value']
    except Exception:
        try:
            return row[0]
        except Exception:
            return default


def send_mailing(msg, count, chat_id, user_id):
    c = get_cursor()
    if count == 0:
        c.execute('SELECT chatId FROM users')
    else:
        c.execute('SELECT chatId FROM users ORDER BY RANDOM() LIMIT ?', (count,))
    users = c.fetchall()
    sent = 0
    for row in users:
        try:
            bot.send_message(row['chatId'], msg, parse_mode='HTML')
            sent += 1
            time.sleep(0.05)
        except Exception:
            pass
    safe_send(chat_id, f"✅ Рассылка завершена! Отправлено {sent} пользователям.")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data

    if data == 'check_sub':
        if check_subscription(user_id):
            safe_send(
                chat_id,
                "✅ Подписка подтверждена! Теперь вы можете пользоваться ботом.",
                reply_markup=main_menu(user_id),
            )
        else:
            safe_answer(call.id, "❌ Вы ещё не подписались!", alert=True)
        return

    if data == 'check_extra_sub':
        if check_extra_subscriptions(user_id):
            safe_send(
                chat_id,
                "✅ Подписка подтверждена! Теперь вы можете пользоваться ботом.",
                reply_markup=main_menu(user_id),
            )
        else:
            safe_answer(call.id, "❌ Вы ещё не подписались на все каналы!", alert=True)
        return

    if data.startswith('claim_task_'):
        try:
            task_id = int(data.split('_')[2])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        success, msg = claim_daily_reward(user_id, task_id)
        safe_answer(call.id, msg, alert=True)
        tasks = get_daily_tasks(user_id)
        if tasks:
            text = "📋 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n"
            kb = InlineKeyboardMarkup()
            for task in tasks:
                if task['completed'] and task['claimed']:
                    status = "✅"
                elif task['completed'] and not task['claimed']:
                    status = "🔄 Готово!"
                else:
                    status = f"🔄 {task['progress']}/{task['target']}"
                text += (
                    f"{status} {task['text']}\n"
                    f"Награда: +{task['reward_money']:.2f} CRF, +{task['reward_exp']} опыта\n\n"
                )
                if task['completed'] and not task['claimed']:
                    kb.add(
                        InlineKeyboardButton(
                            f'🎁 Забрать награду #{task["id"]}',
                            callback_data=f'claim_task_{task["id"]}',
                        )
                    )
            safe_send(chat_id, text, parse_mode='HTML', reply_markup=kb if kb.keyboard else None)
        else:
            safe_send(chat_id, "📭 Сегодня заданий нет.")
        return

    if data.startswith('duel_accept_'):
        try:
            duel_id = int(data.split('_')[2])
        except Exception:
            safe_answer(call.id, "❌ Некорректная дуэль.", alert=True)
            return
        duel = get_duel(duel_id)
        if not duel or duel['status'] != 'waiting':
            safe_send(chat_id, "❌ Дуэль неактивна.")
            safe_answer(call.id)
            return
        if duel['creator_id'] == user_id:
            safe_send(chat_id, "❌ Нельзя принять свою дуэль.")
            safe_answer(call.id)
            return
        amount = duel['amount']
        if get_balance_rub(user_id) < amount:
            safe_send(chat_id, f"❌ Недостаточно средств. Нужно {amount:.2f} ₽")
            safe_answer(call.id)
            return
        limit_ok, limit_msg = check_duel_limit(user_id)
        if not limit_ok:
            safe_send(chat_id, limit_msg)
            safe_answer(call.id)
            return
        add_transaction_rub(user_id, -amount, 'duel_hold', f'Принятие дуэли #{duel_id}')
        c = get_cursor()
        c.execute(
            '''
            UPDATE duels
            SET opponent_id = ?, status = 'active', updated_at = CURRENT_TIMESTAMP,
                elo_opponent = (SELECT elo_rating FROM users WHERE chatId = ?)
            WHERE id = ?
            ''',
            (user_id, user_id, duel_id),
        )
        db.commit()
        if duel['mode'] == 'classic':
            success, msg = resolve_classic_duel(duel_id)
            safe_send(chat_id, msg, reply_markup=duel_kb())
            safe_answer(call.id)
            return
        rps_kb = InlineKeyboardMarkup(row_width=3)
        rps_kb.row(
            InlineKeyboardButton('✊', callback_data=f'rps_{duel_id}_rock'),
            InlineKeyboardButton('✌️', callback_data=f'rps_{duel_id}_scissors'),
            InlineKeyboardButton('✋', callback_data=f'rps_{duel_id}_paper'),
        )
        safe_send(duel['creator_id'], "✊ Сделайте выбор:", reply_markup=rps_kb)
        safe_send(user_id, "✊ Сделайте выбор:", reply_markup=rps_kb)
        safe_send(chat_id, "⚔️ Дуэль начата, ждите выбора.", reply_markup=duel_kb())
        safe_answer(call.id)
        return

    if data.startswith('rps_'):
        parts = data.split('_')
        if len(parts) < 3:
            safe_answer(call.id, "❌ Некорректный выбор.", alert=True)
            return
        try:
            duel_id = int(parts[1])
        except Exception:
            safe_answer(call.id, "❌ Некорректная дуэль.", alert=True)
            return
        choice = parts[2]
        success, msg = set_rps_choice(user_id, duel_id, choice)
        safe_send(chat_id, msg, reply_markup=duel_kb())
        safe_answer(call.id)
        return

    if data == 'duel_back_inline':
        safe_send(chat_id, "Дуэли", reply_markup=duel_kb())
        safe_answer(call.id)
        return

    is_admin_user = user_id in ADMIN_IDS
    is_moderator_user = user_id in MODERATOR_IDS or is_admin_user

    if data.startswith('admin_') and not is_admin_user:
        safe_answer(call.id, '⛔ Доступ запрещён!', alert=True)
        return

    if data.startswith('mod_') and not is_moderator_user:
        safe_answer(call.id, '⛔ Доступ запрещён!', alert=True)
        return

    if data == 'mod_ban':
        user_states[user_id] = {'state': 'mod_ban'}
        safe_send(chat_id, "🚫 Введите ID пользователя для блокировки:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_unban':
        user_states[user_id] = {'state': 'mod_unban'}
        safe_send(chat_id, "✅ Введите ID пользователя для разблокировки:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_balance_rub':
        user_states[user_id] = {'state': 'mod_balance_rub'}
        safe_send(chat_id, "💰 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_balance_crf':
        user_states[user_id] = {'state': 'mod_balance_crf'}
        safe_send(chat_id, "💎 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_level':
        user_states[user_id] = {'state': 'mod_level'}
        safe_send(chat_id, "📈 Введите: <user_id> <уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_vip':
        user_states[user_id] = {'state': 'mod_vip'}
        safe_send(chat_id, "👑 Введите: <user_id> <дни>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'mod_cancel_withdraw':
        user_states[user_id] = {'state': 'mod_cancel_withdraw'}
        safe_send(chat_id, "📛 Введите ID заявки на вывод:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_refresh':
        safe_send(chat_id, "👑 АДМИН-ПАНЕЛЬ\n\nВыберите действие:", parse_mode='HTML', reply_markup=admin_kb())
        safe_answer(call.id, '🔄 Обновлено!')
        return

    if data == 'admin_stats':
        c = get_cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0] or 0
        c.execute('SELECT SUM(balance) FROM crf_balances')
        total_crf = c.fetchone()[0] or 0
        c.execute('SELECT SUM(balance) FROM users')
        total_rub = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM crf_orders WHERE status = "active"')
        active_orders = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM duels WHERE status = "finished"')
        total_duels = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM investments WHERE is_active = 1')
        active_investments = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM crf_stakes WHERE is_active = 1')
        active_stakes = c.fetchone()[0] or 0
        c.execute('SELECT COUNT(*) FROM users WHERE vip_active = 1')
        vip_users = c.fetchone()[0] or 0
        commission_duel = get_stat_value('commission_duel_rub', 0)
        commission_market = get_stat_value('commission_market_rub', 0)
        commission_exchange_rub = get_stat_value('commission_exchange_rub', 0)
        commission_exchange_crf = get_stat_value('commission_exchange_crf', 0)
        commission_invest = get_stat_value('commission_invest_crf', 0)
        total_rub_volume = get_stat_value('total_rub_volume', 0)
        total_crf_volume = get_stat_value('total_crf_volume', 0)
        season = get_active_season()
        season_text = f"Активен: {season['name']}" if season else "Нет активного сезона"
        text = (
            "📊 ДЕТАЛЬНАЯ СТАТИСТИКА БОТА\n\n"
            "👥 Пользователи:\n"
            f"Всего игроков: {total_users}\n"
            f"VIP: {vip_users}\n\n"
            "💎 Криптовалюта CRF:\n"
            f"Всего CRF в обращении: {total_crf:.2f}\n"
            f"Оборот CRF: {total_crf_volume:.2f}\n"
            f"Курс CRF: {get_crf_rate():.4f} ₽\n\n"
            "💰 Финансы:\n"
            f"Всего ₽ в системе: {total_rub:.2f}\n"
            f"Оборот ₽: {total_rub_volume:.2f}\n\n"
            "💸 КОМИССИИ (доход бота):\n"
            f"• С дуэлей (8%): {commission_duel:.2f} ₽\n"
            f"• С рынка (покупка/продажа CRF): {commission_market:.2f} ₽\n"
            f"• С обмена валют (₽): {commission_exchange_rub:.2f} ₽\n"
            f"• С обмена валют (CRF): {commission_exchange_crf:.2f} CRF\n"
            f"• С инвестиций и стейкинга: {commission_invest:.2f} CRF\n\n"
            "🏷️ Рынок:\n"
            f"Активных ордеров: {active_orders}\n\n"
            "⚔️ Дуэли:\n"
            f"Всего проведено: {total_duels}\n\n"
            "📈 Инвестиции и стейкинг:\n"
            f"Активных инвестиций: {active_investments}\n"
            f"Активных стейков: {active_stakes}\n\n"
            "📅 Сезон:\n"
            f"{season_text}"
        )
        safe_send(chat_id, text, parse_mode='HTML')
        safe_answer(call.id)
        return

    if data == 'admin_withdraws':
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE status = 0 ORDER BY created_at ASC LIMIT 1')
        row = c.fetchone()
        if not row:
            safe_send(chat_id, "📭 Нет активных заявок.")
            safe_answer(call.id)
            return
        user = get_user(row['chatId'])
        name = user['firstName'] if user else str(row['chatId'])
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            InlineKeyboardButton('✅ Выплатить', callback_data=f'admin_withdraw_accept_{row["id"]}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'admin_withdraw_reject_{row["id"]}'),
        )
        safe_send(
            chat_id,
            (
                "📛 ЗАЯВКА НА ВЫВОД\n\n"
                f"👤 {name} (ID: {row['chatId']})\n"
                f"💰 Сумма: {row['amount']:.2f} ₽\n"
                f"💳 Карта: {row['wallet']}"
            ),
            parse_mode='HTML',
            reply_markup=kb,
        )
        safe_answer(call.id)
        return

    if data.startswith('admin_withdraw_accept_'):
        try:
            withdraw_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE withdraws SET status = 1 WHERE id = ?', (withdraw_id,))
        db.commit()
        try:
            add_exp(row['chatId'], CONFIG.get('exp_per_withdraw', 20))
        except Exception:
            pass
        try:
            update_task_progress(row['chatId'], 'withdraw', row['amount'])
        except Exception:
            pass
        safe_send(row['chatId'], f"✅ Выплата подтверждена! {row['amount']:.2f} ₽")
        safe_send(chat_id, f"✅ Заявка #{withdraw_id} выплачена.", reply_markup=admin_kb())
        safe_answer(call.id, "✅ Выплачена")
        return

    if data.startswith('admin_withdraw_reject_'):
        try:
            withdraw_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE withdraws SET status = 2 WHERE id = ?', (withdraw_id,))
        db.commit()
        add_transaction_rub(row['chatId'], row['amount'], 'withdraw_reject', f'Возврат по заявке #{withdraw_id}')
        safe_send(row['chatId'], f"❌ Выплата отклонена. {row['amount']:.2f} ₽ возвращены")
        safe_send(chat_id, f"❌ Заявка #{withdraw_id} отклонена.", reply_markup=admin_kb())
        safe_answer(call.id, "❌ Отклонена")
        return

    if data == 'admin_deposits':
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE status = 0 ORDER BY created_at ASC LIMIT 1')
        row = c.fetchone()
        if not row:
            safe_send(chat_id, "📭 Нет активных заявок.")
            safe_answer(call.id)
            return
        user = get_user(row['chatId'])
        name = user['firstName'] if user else str(row['chatId'])
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            InlineKeyboardButton('✅ Подтвердить', callback_data=f'admin_deposit_accept_{row["id"]}'),
            InlineKeyboardButton('❌ Отклонить', callback_data=f'admin_deposit_reject_{row["id"]}'),
        )
        safe_send(
            chat_id,
            (
                "📥 ЗАЯВКА НА ПОПОЛНЕНИЕ\n\n"
                f"👤 {name} (ID: {row['chatId']})\n"
                f"💰 Сумма: {row['amount']:.2f} ₽"
            ),
            parse_mode='HTML',
            reply_markup=kb,
        )
        safe_answer(call.id)
        return

    if data.startswith('admin_deposit_accept_'):
        try:
            deposit_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE id = ? AND status = 0', (deposit_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE deposits SET status = 1 WHERE id = ?', (deposit_id,))
        db.commit()
        add_transaction_rub(row['chatId'], row['amount'], 'deposit', f'Пополнение по заявке #{deposit_id}')
        try:
            update_task_progress(row['chatId'], 'deposit', row['amount'])
        except Exception:
            pass
        safe_send(row['chatId'], f"✅ Пополнение подтверждено! На баланс зачислено {row['amount']:.2f} ₽")
        safe_send(chat_id, f"✅ Заявка #{deposit_id} подтверждена.", reply_markup=admin_kb())
        safe_answer(call.id, "✅ Подтверждено")
        return

    if data.startswith('admin_deposit_reject_'):
        try:
            deposit_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректная заявка.", alert=True)
            return
        c = get_cursor()
        c.execute('SELECT * FROM deposits WHERE id = ? AND status = 0', (deposit_id,))
        row = c.fetchone()
        if not row:
            safe_answer(call.id, "❌ Заявка не найдена.", alert=True)
            return
        c.execute('UPDATE deposits SET status = 2 WHERE id = ?', (deposit_id,))
        db.commit()
        safe_send(row['chatId'], f"❌ Заявка на пополнение #{deposit_id} отклонена.")
        safe_send(chat_id, f"❌ Заявка #{deposit_id} отклонена.", reply_markup=admin_kb())
        safe_answer(call.id, "❌ Отклонено")
        return

    if data == 'admin_replenish_settings':
        c = get_cursor()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_card'")
        card = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_holder'")
        holder = c.fetchone()
        c.execute("SELECT value FROM settings WHERE key = 'replenish_bank'")
        bank = c.fetchone()
        text = (
            "🏦 ТЕКУЩИЕ РЕКВИЗИТЫ ПОПОЛНЕНИЯ\n\n"
            f"💳 Карта: {card['value'] if card else 'Не указано'}\n"
            f"👤 Держатель: {holder['value'] if holder else 'Не указано'}\n"
            f"🏦 Банк: {bank['value'] if bank else 'Не указано'}\n\n"
            "Для изменения отправьте новую карту, держателя и банк через запятую:\n"
            "<номер карты>, <держатель>, <банк>"
        )
        user_states[user_id] = {'state': 'admin_replenish_update'}
        safe_send(chat_id, text, parse_mode='HTML', reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_broadcast':
        user_states[user_id] = {'state': 'admin_broadcast'}
        safe_send(chat_id, "📟 Введите количество пользователей для рассылки (0 - всем):", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_balance_rub':
        user_states[user_id] = {'state': 'admin_balance_rub'}
        safe_send(chat_id, "💰 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_balance_crf':
        user_states[user_id] = {'state': 'admin_balance_crf'}
        safe_send(chat_id, "💎 Введите: <user_id> <сумма>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_crf_rate':
        user_states[user_id] = {'state': 'admin_crf_rate'}
        safe_send(chat_id, "📈 Введите новый курс CRF в ₽:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_requests':
        c = get_cursor()
        c.execute(
            '''
            SELECT * FROM moderator_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 20
            '''
        )
        rows = c.fetchall()
        if not rows:
            safe_send(chat_id, "📭 Нет активных запросов модераторов.")
            safe_answer(call.id)
            return
        text = "📋 ЗАПРОСЫ МОДЕРАТОРОВ\n\n"
        for row in rows:
            text += (
                f"🆔 #{row['id']}\n"
                f"👤 Модератор: {row['moderator_id']}\n"
                f"🎯 Цель: {row['target_user_id']}\n"
                f"⚙️ Действие: {row['action_type']}\n"
                f"📝 Данные: {row['data'] or '{}'}\n"
                f"🕒 {row['created_at']}\n\n"
            )
        safe_send(chat_id, text, parse_mode='HTML')
        safe_answer(call.id)
        return

    if data == 'admin_transactions':
        user_states[user_id] = {'state': 'admin_transactions'}
        safe_send(chat_id, "📊 Введите ID пользователя:", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_give_level':
        user_states[user_id] = {'state': 'admin_give_level'}
        safe_send(chat_id, "📈 Введите: <user_id> <уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_change_refs':
        user_states[user_id] = {'state': 'admin_change_refs'}
        safe_send(chat_id, "📊 Введите: <user_id> <реф. уровень>", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_clear_stats':
        c = get_cursor()
        c.execute('UPDATE stats SET value = 0')
        db.commit()
        safe_send(chat_id, "🗑️ Статистика очищена.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data == 'admin_seasons':
        season = get_active_season()
        if season:
            text = (
                "📅 УПРАВЛЕНИЕ СЕЗОНАМИ\n\n"
                f"Сейчас активен сезон: {season['name']}\n"
                f"Призовой фонд: {season['prize_pool']:.2f} ₽\n\n"
                "Введите название нового сезона:"
            )
        else:
            text = "📅 Введите название нового сезона:"
        user_states[user_id] = {'state': 'admin_seasons_create_name'}
        safe_send(chat_id, text, reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_task_subscribe':
        user_states[user_id] = {'state': 'admin_task_subscribe_channel'}
        safe_send(chat_id, "📝 Введите username канала для задания (без @):", reply_markup=cancel_kb())
        safe_answer(call.id)
        return

    if data == 'admin_tasks_list':
        c = get_cursor()
        c.execute('SELECT * FROM tasks WHERE active = 1 ORDER BY id ASC')
        tasks = c.fetchall()
        if not tasks:
            safe_send(chat_id, "📭 Активных заданий нет.")
            safe_answer(call.id)
            return
        text = "📋 АКТИВНЫЕ ЗАДАНИЯ (подписка)\n\n"
        kb = InlineKeyboardMarkup(row_width=2)
        for task in tasks:
            text += f"🆔 {task['id']} | @{task['channel']} → {task['reward']:.2f} CRF\n"
            kb.add(
                InlineKeyboardButton(
                    f'❌ Удалить #{task["id"]}',
                    callback_data=f'admin_task_delete_{task["id"]}',
                )
            )
            kb.add(
                InlineKeyboardButton(
                    f'✏️ Изменить награду #{task["id"]}',
                    callback_data=f'admin_task_edit_{task["id"]}',
                )
            )
        kb.add(InlineKeyboardButton('🗑️ Удалить все', callback_data='admin_task_delete_all'))
        kb.add(InlineKeyboardButton('🔙 Назад', callback_data='admin_refresh'))
        safe_send(chat_id, text, parse_mode='HTML', reply_markup=kb)
        safe_answer(call.id)
        return

    if data == 'admin_task_delete_all':
        c = get_cursor()
        c.execute('DELETE FROM tasks WHERE active = 1')
        db.commit()
        safe_send(chat_id, "🗑️ Все задания удалены.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data.startswith('admin_task_delete_'):
        try:
            task_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        c = get_cursor()
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        db.commit()
        safe_send(chat_id, f"✅ Задание #{task_id} удалено.", reply_markup=admin_kb())
        safe_answer(call.id)
        return

    if data.startswith('admin_task_edit_'):
        try:
            task_id = int(data.split('_')[3])
        except Exception:
            safe_answer(call.id, "❌ Некорректное задание.", alert=True)
            return
        user_states[user_id] = {'state': 'admin_task_edit_reward', 'task_id': task_id}
        safe_send(
            chat_id,
            f"✏️ Введите новую награду (в CRF) для задания #{task_id}:",
            reply_markup=cancel_kb(),
        )
        safe_answer(call.id)
        return

    safe_answer(call.id)


@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_states(m):
    user_id = m.from_user.id
    if user_id not in user_states:
        return
    state = user_states[user_id].get('state')

    if m.text == '❌ Отменить':
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Отменено.', reply_markup=main_menu(user_id))
        return

    if state == 'verification':
        code = m.text.strip()
        saved_code = user_states[user_id].get('code')
        saved_time = user_states[user_id].get('time')
        if saved_time and datetime.now() - saved_time > timedelta(minutes=10):
            del user_states[user_id]
            safe_send(m.chat.id, '❌ Код истёк. Начните заново.', reply_markup=main_menu(user_id))
        elif code == saved_code:
            update_field(user_id, 'is_verified', 1)
            del user_states[user_id]
            safe_send(m.chat.id, '✅ ВЕРИФИКАЦИЯ ПРОЙДЕНА!', reply_markup=main_menu(user_id))
        else:
            safe_send(m.chat.id, '❌ Неверный код. Попробуйте снова.', reply_markup=cancel_kb())

    elif state == 'exchange_rub_to_crf':
        try:
            amount_rub = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount_rub <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        if get_balance_rub(user_id) < amount_rub:
            safe_send(m.chat.id, f"❌ Недостаточно ₽. У вас {get_balance_rub(user_id):.2f}")
            return
        rate = get_crf_rate()
        commission = amount_rub * (CONFIG.get('exchange_commission_percent', 10.0) / 100.0)
        amount_crf = (amount_rub - commission) / rate
        add_transaction_rub(
            user_id,
            -amount_rub,
            'exchange_rub_to_crf',
            f'Обмен {amount_rub:.2f} ₽ на CRF (комиссия {commission:.2f} ₽)',
        )
        add_transaction_rub(0, commission, 'exchange_commission_rub', f'Комиссия за обмен ₽→CRF от {user_id}')
        c = get_cursor()
        c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_exchange_rub"', (commission,))
        db.commit()
        add_transaction_crf(
            user_id,
            amount_crf,
            'exchange_rub_to_crf',
            f'Обмен {amount_rub:.2f} ₽ на CRF по курсу {rate:.4f}',
        )
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Обмен выполнен! Вы получили {amount_crf:.2f} CRF за "
                f"{amount_rub:.2f} ₽ (комиссия {commission:.2f} ₽)"
            ),
            reply_markup=exchange_kb(),
        )

    elif state == 'exchange_crf_to_rub':
        try:
            amount_crf = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount_crf <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        if get_balance_crf(user_id) < amount_crf:
            safe_send(m.chat.id, f"❌ Недостаточно CRF. У вас {get_balance_crf(user_id):.2f}")
            return
        rate = get_crf_rate()
        commission = amount_crf * (CONFIG.get('exchange_commission_percent', 10.0) / 100.0)
        amount_rub = (amount_crf - commission) * rate
        add_transaction_crf(
            user_id,
            -amount_crf,
            'exchange_crf_to_rub',
            f'Обмен {amount_crf:.2f} CRF на ₽ (комиссия {commission:.2f} CRF)',
        )
        add_transaction_crf(0, commission, 'exchange_commission_crf', f'Комиссия за обмен CRF→₽ от {user_id}')
        c = get_cursor()
        c.execute('UPDATE stats SET value = value + ? WHERE key = "commission_exchange_crf"', (commission,))
        db.commit()
        add_transaction_rub(
            user_id,
            amount_rub,
            'exchange_crf_to_rub',
            f'Обмен {amount_crf:.2f} CRF на ₽ по курсу {rate:.4f}',
        )
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Обмен выполнен! Вы получили {amount_rub:.2f} ₽ за "
                f"{amount_crf:.2f} CRF (комиссия {commission:.2f} CRF)"
            ),
            reply_markup=exchange_kb(),
        )

    elif state == 'withdraw_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        balance = user_states[user_id].get('balance', 0)
        if amount <= 0 or amount > balance:
            safe_send(m.chat.id, f"❌ Сумма должна быть от 0 до {balance:.2f}")
            return
        level, _ = get_user_level(user_id)
        if level < CONFIG.get('withdraw_min_level', 2):
            del user_states[user_id]
            safe_send(
                m.chat.id,
                f"❌ Вывод доступен с {CONFIG.get('withdraw_min_level', 2)} уровня.",
                reply_markup=main_menu(user_id),
            )
            return
        fee_percent = get_level_bonuses(level)['withdraw_fee']
        fee = amount * (fee_percent / 100.0)
        net = amount - fee
        if net <= 0:
            safe_send(m.chat.id, f"❌ Сумма слишком мала после комиссии ({fee_percent:.1f}%).")
            return
        user_states[user_id] = {'state': 'withdraw_wallet', 'amount': amount, 'net': net, 'fee': fee}
        safe_send(
            m.chat.id,
            f"💳 Введите номер карты или кошелёк Юмани для вывода {net:.2f} ₽ (комиссия {fee:.2f} ₽):",
            reply_markup=cancel_kb(),
        )

    elif state == 'withdraw_wallet':
        wallet = m.text.strip()
        if not wallet:
            safe_send(m.chat.id, "❌ Введите реквизиты.")
            return
        amount = user_states[user_id].get('amount')
        net = user_states[user_id].get('net')
        add_transaction_rub(user_id, -amount, 'withdraw_hold', f'Заявка на вывод {amount:.2f} ₽')
        c = get_cursor()
        c.execute('INSERT INTO withdraws (chatId, amount, wallet) VALUES (?, ?, ?)', (user_id, net, wallet))
        db.commit()
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    f"📛 Новая заявка на вывод от {user_id}: {net:.2f} ₽ на {wallet}",
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка на вывод {net:.2f} ₽ создана. Ожидайте обработки.",
            reply_markup=cabinet_kb(),
        )

    elif state == 'deposit_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount <= 0:
            safe_send(m.chat.id, "❌ Сумма должна быть > 0")
            return
        c = get_cursor()
        c.execute('INSERT INTO deposits (chatId, amount) VALUES (?, ?)', (user_id, amount))
        db.commit()
        deposit_id = c.lastrowid
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    f"📥 Новая заявка на пополнение #{deposit_id} от {user_id}: {amount:.2f} ₽",
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка на пополнение #{deposit_id} на {amount:.2f} ₽ создана. Ожидайте подтверждения администратором.",
            reply_markup=cabinet_kb(),
        )

    elif state == 'support':
        msg_text = m.text
        c = get_cursor()
        c.execute('INSERT INTO tickets (user_id, message, status) VALUES (?, ?, "open")', (user_id, msg_text))
        db.commit()
        ticket_id = c.lastrowid
        for admin in ADMIN_IDS:
            try:
                bot.send_message(
                    admin,
                    (
                        f"🆘 Новый тикет #{ticket_id} от {user_id}:\n{msg_text}\n\n"
                        f"Ответьте командой: /reply_ticket {ticket_id} <текст>"
                    ),
                    parse_mode='HTML',
                )
            except Exception:
                pass
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Сообщение отправлено администраторам.', reply_markup=main_menu(user_id))

    elif state == 'duel_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, '❌ Введите число.')
            return
        if amount < 1:
            safe_send(m.chat.id, '❌ Минимальная ставка 1 ₽')
            return
        mode = user_states[user_id].get('mode', 'classic')
        success, msg = create_duel(user_id, amount, mode)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=duel_kb())

    elif state == 'promo_mailing_users':
        try:
            count = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите целое число.")
            return
        c = get_cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0] or 0
        if count < 0 or count > total:
            safe_send(m.chat.id, f"❌ Количество должно быть от 0 до {total}")
            return
        price = (
            count * CONFIG.get('promo_mailing_price_per_user', 0.3)
            if count > 0
            else total * CONFIG.get('promo_mailing_price_per_user', 0.3)
        )
        if get_balance_rub(user_id) < price:
            del user_states[user_id]
            safe_send(m.chat.id, f"❌ Недостаточно средств. Нужно {price:.2f} ₽. Пополните баланс.")
            return
        user_states[user_id] = {'state': 'promo_mailing_msg', 'count': count, 'price': price}
        safe_send(
            m.chat.id,
            (
                "📨 Отправьте сообщение для рассылки (текст или перешлите сообщение).\n"
                f"Будет отправлено {count if count > 0 else total} пользователям. "
                f"Стоимость: {price:.2f} ₽."
            ),
            reply_markup=cancel_kb(),
        )

    elif state == 'promo_mailing_msg':
        count = user_states[user_id].get('count', 0)
        price = user_states[user_id].get('price', 0)
        add_transaction_rub(user_id, -price, 'promo_mailing', f'Рассылка сообщения {count} пользователям')
        add_transaction_rub(0, price, 'promo_mailing_income', f'Доход от рассылки от {user_id}')
        c = get_cursor()
        c.execute(
            '''
            INSERT INTO promotions (user_id, type, message, price, status)
            VALUES (?, 'mailing', ?, ?, 'active')
            ''',
            (user_id, m.text, price),
        )
        db.commit()
        threading.Thread(target=send_mailing, args=(m.text, count, m.chat.id, user_id)).start()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Рассылка запущена! Стоимость: {price:.2f} ₽. "
                f"Сообщение будет доставлено {count if count > 0 else 'всем'} пользователям."
            ),
        )

    elif state == 'promo_channel_channel':
        channel = clean_channel(m.text)
        if not channel:
            safe_send(m.chat.id, "❌ Некорректный username")
            return
        user_states[user_id] = {'state': 'promo_channel_hours', 'channel': channel}
        safe_send(m.chat.id, "⏱️ Введите количество часов рекламы (цена 50₽/час):", reply_markup=cancel_kb())

    elif state == 'promo_channel_hours':
        try:
            hours = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите целое число часов.")
            return
        if hours <= 0:
            safe_send(m.chat.id, "❌ Количество часов должно быть > 0")
            return
        price = hours * CONFIG.get('promo_channel_price_per_hour', 50.0)
        channel = user_states[user_id].get('channel')
        if get_balance_rub(user_id) < price:
            del user_states[user_id]
            safe_send(m.chat.id, f"❌ Недостаточно средств. Нужно {price:.2f} ₽.")
            return
        add_transaction_rub(user_id, -price, 'promo_channel', f'Реклама канала @{channel} на {hours} ч')
        add_transaction_rub(0, price, 'promo_channel_income', f'Доход от рекламы канала @{channel}')
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=hours)
        c = get_cursor()
        c.execute(
            '''
            INSERT INTO promotions (user_id, type, channel, price, hours, start_time, end_time, status)
            VALUES (?, 'channel', ?, ?, ?, ?, ?, 'active')
            ''',
            (user_id, channel, price, hours, start_time.isoformat(), end_time.isoformat()),
        )
        db.commit()
        c.execute('INSERT OR IGNORE INTO promo_subscriptions (user_id, channel) VALUES (?, ?)', (user_id, channel))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            (
                f"✅ Реклама канала @{channel} запущена на {hours} часов! "
                f"Стоимость: {price:.2f} ₽. Канал добавлен в обязательные подписки для всех пользователей."
            ),
        )

    elif state == 'invest_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount < CONFIG.get('investment_min', 10):
            safe_send(m.chat.id, f"❌ Минимальная сумма: {CONFIG.get('investment_min', 10)} CRF")
            return
        days = user_states[user_id].get('days', 1)
        success, msg = create_investment_crf(user_id, amount, days)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=invest_kb())

    elif state == 'stake_amount':
        try:
            amount = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if amount < 1:
            safe_send(m.chat.id, "❌ Минимальная сумма: 1 CRF")
            return
        days = user_states[user_id].get('days', 7)
        success, msg = stake_crf(user_id, amount, days)
        del user_states[user_id]
        safe_send(m.chat.id, msg, reply_markup=invest_kb())

    elif state == 'admin_replenish_update':
        parts = [part.strip() for part in m.text.split(',')]
        if len(parts) < 3:
            safe_send(m.chat.id, "❌ Неверный формат. Используйте: карта, держатель, банк")
            return
        c = get_cursor()
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_card"', (parts[0],))
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_holder"', (parts[1],))
        c.execute('UPDATE settings SET value = ? WHERE key = "replenish_bank"', (parts[2],))
        db.commit()
        del user_states[user_id]
        safe_send(m.chat.id, "✅ Реквизиты пополнения обновлены!", reply_markup=admin_kb())

    elif state == 'admin_task_edit_reward':
        try:
            new_reward = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if new_reward <= 0:
            safe_send(m.chat.id, "❌ Награда должна быть > 0")
            return
        task_id = user_states[user_id].get('task_id')
        c = get_cursor()
        c.execute('UPDATE tasks SET reward = ? WHERE id = ?', (new_reward, task_id))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Награда для задания #{task_id} изменена на {new_reward:.2f} CRF",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_balance_rub':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        add_transaction_rub(target, amount, 'admin_balance', 'Админ изменил баланс ₽')
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Баланс ₽ пользователя {target} изменён на {amount:.2f}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_balance_crf':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        add_transaction_crf(target, amount, 'admin_balance_crf', 'Админ изменил баланс CRF')
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Баланс CRF пользователя {target} изменён на {amount:.2f}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_crf_rate':
        try:
            new_rate = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if new_rate <= 0:
            safe_send(m.chat.id, "❌ Курс должен быть > 0")
            return
        update_crf_rate(new_rate)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Курс CRF обновлён: 1 CRF = {new_rate:.4f} ₽",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_transactions':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        user = get_user(target)
        if not user:
            del user_states[user_id]
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (target,))
        rub = c.fetchall()
        c.execute('SELECT * FROM crf_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (target,))
        crf = c.fetchall()
        text = f"📊 Транзакции пользователя {target}\n\n"
        text += "💰 ₽:\n"
        for row in rub:
            sign = '+' if row['amount'] > 0 else ''
            text += f"{row['type']}: {sign}{row['amount']:.2f} ₽ – {row['description']}\n"
        text += "\n💎 CRF:\n"
        for row in crf:
            sign = '+' if row['amount'] > 0 else ''
            text += f"{row['type']}: {sign}{row['amount']:.2f} CRF – {row['description']}\n"
        del user_states[user_id]
        safe_send(m.chat.id, text, parse_mode='HTML')

    elif state == 'admin_give_level':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <уровень>")
            return
        try:
            target = int(parts[0])
            level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if level < 1:
            safe_send(m.chat.id, "❌ Уровень должен быть >= 1")
            return
        update_field(target, 'level', level)
        update_field(target, 'exp', 0)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Уровень пользователя {target} установлен на {level}, опыт сброшен",
            reply_markup=main_menu(user_id),
        )
        safe_send(target, f"👑 Администратор установил ваш уровень: {level}")

    elif state == 'admin_change_refs':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <реф. уровень>")
            return
        try:
            target = int(parts[0])
            ref_level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if ref_level < 1 or ref_level > 3:
            safe_send(m.chat.id, "❌ Реф. уровень должен быть от 1 до 3")
            return
        update_field(target, 'ref_level', ref_level)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Реф. уровень пользователя {target} установлен на {ref_level}",
            reply_markup=main_menu(user_id),
        )
        safe_send(target, f"👑 Администратор изменил ваш реферальный уровень: {ref_level}")

    elif state == 'admin_seasons_create_name':
        name = m.text.strip()
        if not name:
            safe_send(m.chat.id, "❌ Название не может быть пустым.")
            return
        user_states[user_id] = {'state': 'admin_seasons_create_prize', 'name': name}
        safe_send(m.chat.id, "💰 Введите призовой фонд сезона (в ₽):", reply_markup=cancel_kb())

    elif state == 'admin_seasons_create_prize':
        try:
            prize = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if prize < 0:
            safe_send(m.chat.id, "❌ Сумма не может быть отрицательной.")
            return
        name = user_states[user_id].get('name')
        season_id = create_season(name, prize)
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Сезон '{name}' создан! ID: {season_id}",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_task_subscribe_channel':
        channel = clean_channel(m.text)
        if not channel:
            safe_send(m.chat.id, "❌ Некорректный username")
            return
        user_states[user_id] = {'state': 'admin_task_subscribe_reward', 'channel': channel}
        safe_send(m.chat.id, f"💰 Введите награду в CRF за подписку на @{channel}:", reply_markup=cancel_kb())

    elif state == 'admin_task_subscribe_reward':
        try:
            reward = float(m.text.replace(',', '.'))
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        if reward <= 0:
            safe_send(m.chat.id, "❌ Награда должна быть > 0")
            return
        channel = user_states[user_id].get('channel')
        c = get_cursor()
        c.execute('INSERT INTO tasks (channel, reward) VALUES (?, ?)', (channel, reward))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Задание создано! Подписка на @{channel} даёт {reward:.2f} CRF",
            reply_markup=main_menu(user_id),
        )

    elif state == 'admin_broadcast':
        try:
            count = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите число.")
            return
        user_states[user_id] = {'state': 'admin_broadcast_msg', 'count': count}
        safe_send(m.chat.id, "📨 Отправьте сообщение:")

    elif state == 'admin_broadcast_msg':
        count = user_states[user_id].get('count', 0)
        c = get_cursor()
        if count == 0:
            c.execute('SELECT chatId FROM users')
        else:
            c.execute('SELECT chatId FROM users ORDER BY RANDOM() LIMIT ?', (count,))
        rows = c.fetchall()
        failed = 0
        for row in rows:
            try:
                try:
                    target_chat = row['chatId']
                except Exception:
                    target_chat = row[0]
                bot.copy_message(target_chat, m.chat.id, m.message_id)
                time.sleep(0.05)
            except Exception:
                failed += 1
        del user_states[user_id]
        safe_send(m.chat.id, f"✅ Рассылка завершена! Не доставлено: {failed}", reply_markup=main_menu(user_id))

    elif state == 'mod_ban':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'ban', target, '{}'),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на блокировку {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_unban':
        try:
            target = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'unban', target, '{}'),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на разблокировку {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_balance_rub':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'balance_rub', target, json.dumps({'amount': amount})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение баланса ₽ {target} на {amount:.2f} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_balance_crf':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <сумма>")
            return
        try:
            target = int(parts[0])
            amount = float(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'balance_crf', target, json.dumps({'amount': amount})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение баланса CRF {target} на {amount:.2f} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_level':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <уровень>")
            return
        try:
            target = int(parts[0])
            level = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if level < 1:
            safe_send(m.chat.id, "❌ Уровень должен быть >= 1")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'change_level', target, json.dumps({'level': level})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на изменение уровня {target} на {level} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_vip':
        parts = m.text.split()
        if len(parts) < 2:
            safe_send(m.chat.id, "❌ Формат: <user_id> <дни>")
            return
        try:
            target = int(parts[0])
            days = int(parts[1])
        except Exception:
            safe_send(m.chat.id, "❌ Неверный формат")
            return
        if not get_user(target):
            safe_send(m.chat.id, "❌ Пользователь не найден")
            return
        if days < 1:
            safe_send(m.chat.id, "❌ Дней должно быть >= 1")
            return
        c = get_cursor()
        c.execute(
            'INSERT INTO moderator_requests (moderator_id, action_type, target_user_id, data) VALUES (?, ?, ?, ?)',
            (user_id, 'give_vip', target, json.dumps({'days': days})),
        )
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Запрос на выдачу VIP на {days} дней пользователю {target} отправлен администраторам.",
            reply_markup=main_menu(user_id),
        )

    elif state == 'mod_cancel_withdraw':
        try:
            withdraw_id = int(m.text)
        except Exception:
            safe_send(m.chat.id, "❌ Введите ID заявки")
            return
        c = get_cursor()
        c.execute('SELECT * FROM withdraws WHERE id = ? AND status = 0', (withdraw_id,))
        row = c.fetchone()
        if not row:
            safe_send(m.chat.id, "❌ Заявка не найдена или уже обработана")
            return
        add_transaction_rub(row['chatId'], row['amount'], 'withdraw_cancel', f'Отмена заявки модератором #{withdraw_id}')
        c.execute('UPDATE withdraws SET status = 2 WHERE id = ?', (withdraw_id,))
        db.commit()
        del user_states[user_id]
        safe_send(
            m.chat.id,
            f"✅ Заявка #{withdraw_id} отменена, средства возвращены.",
            reply_markup=main_menu(user_id),
        )

    else:
        del user_states[user_id]
        safe_send(m.chat.id, '✅ Отменено.', reply_markup=main_menu(user_id))


@bot.message_handler(func=lambda m: m.text == '💸 Вывести ₽')
def withdraw_btn(m):
    user_id = m.from_user.id
    balance = get_balance_rub(user_id)
    level, _ = get_user_level(user_id)
    fee_percent = get_level_bonuses(level)['withdraw_fee']
    user_states[user_id] = {'state': 'withdraw_amount', 'balance': balance}
    safe_send(
        m.chat.id,
        (
            f"💸 Ваш баланс: {balance:.2f} ₽\n"
            f"Комиссия вывода для вашего уровня: {fee_percent:.1f}%\n"
            "Введите сумму для вывода:"
        ),
        reply_markup=cancel_kb(),
    )


@bot.message_handler(func=lambda m: m.text == '💳 Пополнить')
def deposit_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_card'")
    card = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_holder'")
    holder = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key = 'replenish_bank'")
    bank = c.fetchone()
    text = (
        "💳 ПОПОЛНЕНИЕ БАЛАНСА\n\n"
        f"Карта: {card['value'] if card else CONFIG.get('replenish_card', 'Не указано')}\n"
        f"Держатель: {holder['value'] if holder else CONFIG.get('replenish_holder', 'Не указано')}\n"
        f"Банк: {bank['value'] if bank else CONFIG.get('replenish_bank', 'Не указано')}\n\n"
        "После оплаты введите сумму пополнения в ₽:"
    )
    user_states[user_id] = {'state': 'deposit_amount'}
    safe_send(m.chat.id, text, reply_markup=cancel_kb())


@bot.message_handler(func=lambda m: m.text == '📊 История')
def cabinet_history_btn(m):
    user_id = m.from_user.id
    c = get_cursor()
    c.execute('SELECT * FROM withdraws WHERE chatId = ? ORDER BY created_at DESC LIMIT 10', (user_id,))
    withdraws = c.fetchall()
    c.execute('SELECT * FROM deposits WHERE chatId = ? ORDER BY created_at DESC LIMIT 10', (user_id,))
    deposits = c.fetchall()
    status_map = {0: '⏳ В обработке', 1: '✅ Подтверждено', 2: '❌ Отклонено'}
    text = "📊 ИСТОРИЯ ЗАЯВОК\n\n"
    if deposits:
        text += "📥 Пополнения:\n"
        for row in deposits:
            text += (
                f"#{row['id']} • {row['amount']:.2f} ₽ • "
                f"{status_map.get(row['status'], '❓')} • {row['created_at']}\n"
            )
        text += "\n"
    if withdraws:
        text += "📛 Выводы:\n"
        for row in withdraws:
            text += (
                f"#{row['id']} • {row['amount']:.2f} ₽ • "
                f"{status_map.get(row['status'], '❓')} • {row['created_at']}\n"
            )
        text += "\n"
    if not deposits and not withdraws:
        text += "Нет заявок."
    safe_send(m.chat.id, text, reply_markup=cabinet_kb())


@bot.message_handler(func=lambda m: m.text == '📋 Задания')
def tasks_btn(m):
    user_id = m.from_user.id
    tasks = get_daily_tasks(user_id)
    if not tasks:
        safe_send(m.chat.id, "📭 Сегодня заданий нет.", reply_markup=main_menu(user_id))
        return
    text = "📋 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ\n\n"
    kb = InlineKeyboardMarkup()
    for task in tasks:
        if task['completed'] and task['claimed']:
            status = "✅"
        elif task['completed'] and not task['claimed']:
            status = "🔄 Готово!"
        else:
            status = f"🔄 {task['progress']}/{task['target']}"
        text += (
            f"{status} {task['text']}\n"
            f"Награда: +{task['reward_money']:.2f} CRF, +{task['reward_exp']} опыта\n\n"
        )
        if task['completed'] and not task['claimed']:
            kb.add(
                InlineKeyboardButton(
                    f'🎁 Забрать награду #{task["id"]}',
                    callback_data=f'claim_task_{task["id"]}',
                )
            )
    safe_send(m.chat.id, text, parse_mode='HTML', reply_markup=kb if kb.keyboard else None)


@bot.message_handler(func=lambda m: m.text == '🎁 Бонус')
def bonus_btn(m):
    user_id = m.from_user.id
    today = datetime.now().date().isoformat()
    last = get_field(user_id, 'lastDailyBonus', '')
    if last == today:
        safe_send(m.chat.id, "🎁 Вы уже получали бонус сегодня. Приходите завтра!")
        return
    level, _ = get_user_level(user_id)
    bonus_max = get_level_bonuses(level)['bonus_max_crf']
    bonus = round(random.uniform(CONFIG.get('bonus_min_crf', 0.1), bonus_max), 2)
    add_transaction_crf(user_id, bonus, 'daily_bonus', f'Ежедневный бонус (уровень {level})')
    add_exp(user_id, CONFIG.get('exp_per_bonus', 5))
    update_field(user_id, 'lastDailyBonus', today)
    if is_vip(user_id):
        add_transaction_crf(user_id, bonus, 'vip_bonus_double', 'Удвоение VIP бонуса')
        bonus *= 2
    safe_send(
        m.chat.id,
        f"🎁 Вы получили ежедневный бонус: {bonus:.2f} CRF\n+{CONFIG.get('exp_per_bonus', 5)} опыта",
        parse_mode='HTML',
    )


@bot.message_handler(func=lambda m: m.text == '🎲 Колесо удачи')
def wheel_btn(m):
    user_id = m.from_user.id
    today = datetime.now().date().isoformat()
    last = get_field(user_id, 'lastSpin', '')
    if last == today:
        safe_send(m.chat.id, "🎲 Вы уже крутили колесо сегодня. Приходите завтра!")
        return
    level, _ = get_user_level(user_id)
    spin_max = get_level_bonuses(level)['spin_max_crf']
    reward = random.choice(CONFIG.get('spin_rewards_crf', [0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0]))
    reward = min(reward, spin_max)
    add_transaction_crf(user_id, reward, 'spin_win', 'Колесо удачи (выигрыш CRF)')
    add_exp(user_id, CONFIG.get('exp_per_spin', 3))
    update_field(user_id, 'lastSpin', today)
    safe_send(
        m.chat.id,
        f"🎲 Колесо удачи!\n\nВы выиграли {reward:.2f} CRF!\n+{CONFIG.get('exp_per_spin', 3)} опыта",
        parse_mode='HTML',
    )


if __name__ == '__main__':
    bot.infinity_polling(timeout=60)
