#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
To'liq Telegram Trading Bot - single file (bot.py)
- PyTelegramBotAPI (telebot) asosida
- SQLite saqlash (users, transactions, prices, trades, withdraws)
- Bozor narxlari avtomatik yangilanadi (Binance, yfinance fallback)
- Savdo simulyatori: Short (10s x2), Middle (20s x4), Long (50s x8)
- Depozit va Withdraw: admin tasdiqlashi uchun so‘rovlar
- 3 til: uz, ru, en (matnlar TEXTS dict ichida)
- Admin: /adminpanel, /approve_withdraw id idx, /reject_withdraw id idx, /win user_id trade_id amount, /lose ...
- NOTE: O'zgartirish uchun # ADMIN: ... izohlarni qidiring
"""

import os
import time
import json
import random
import threading
import sqlite3
import traceback
from datetime import datetime

import telebot
from telebot import types
import requests

# -----------------------------
# CONFIG - ADMIN o'zgarishi mumkin
# -----------------------------
TOKEN = os.getenv("8311598762:AAF4U6q2wr8aJ0wfDvmkP3pe6_EAerZLLYA") or "YOUR_BOT_TOKEN_HERE"   # ADMIN: shu yerga tokeningizni qo'ying yoki GitHub secrets orqali BOT_TOKEN o'zgaruvchisidan foydalaning
ADMIN_ID = int(os.getenv("ADMIN_ID") or 123456789)        # ADMIN: o'zingizni telegram idingiz bilan almashtiring
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID") or ADMIN_ID)  # ADMIN: foydalanuvchi so'rovlarini oladigan kanal yoki sizning ID

DB_PATH = "trading_bot.db"
WITHDRAW_FILE = "withdraws.json"  # zaxira (optional)
PRICE_UPDATE_INTERVAL = 60  # soniya - bozor narxlarini yangilash oralig'i

# API keys (agar kerak bo'lsa)
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")
# -----------------------------

bot = telebot.TeleBot(TOKEN)

# -----------------------------
# Matnlar (uz, ru, en)
# O'zgartirish joylari uchun izohlar bilan
# -----------------------------
TEXTS = {
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "main_menu": "📋 Asosiy menyu:",
        "balance": "💰 Balans: {} USD",
        "deposit": "➕ Depozit",
        "withdraw": "💸 Pul yechish",
        "market": "💹 Bozor",
        "trade": "📊 Savdo",
        "help": "ℹ️ Yordam",
        "back": "⬅️ Orqaga",
        "home": "🏠 Bosh menyu",
        "admin": "⚙️ Admin panel",
        "deposit_info": "Depozit uchun hisob raqamlar admin tomonidan taqdim etiladi. Depozitni bajargach, skrinshot yuboring va adminga xabar bering.",
        "withdraw_request_received": "✅ So'rovingiz qabul qilindi. Admin tez orada ko'rib chiqadi.",
        "withdraw_ask_details": "Iltimos, yechish uchun ma'lumot va summani kiriting (masalan: `8600123456789012 50000`).",
        "withdraw_admin_notify": "💳 Yangi yechish so'rovi!\n👤 User: {}\nValyuta: {}\nMa'lumot: {}\nSumma: {}\nTime: {}",
        "trade_start_choose": "Savdo uchun aktiv tanlang:",
        "trade_time_choose": "Vaqtni tanlang (Short/ Middle/ Long):",
        "trade_direction_choose": "Prognoz tanlang: ⬆️ / ⬇️ / ➖",
        "trade_in_progress": "⏳ Savdo o'tmoqda... natija keyinroq e'lon qilinadi.",
        "trade_result_win": "🎉 Siz yutdingiz! {} USD balansga qo‘shildi.",
        "trade_result_lose": "😔 Siz yutqazdingiz. {} USD balansdan ayirildi.",
        "invalid_format": "❌ Format xato. Iltimos ko'rsatmalarga rioya qiling.",
        "min_deposit": "Min deposit: 15 USD, Max: 3000 USD.",
        "upload_screenshot": "Iltimos to'lov skrinshotini yuboring (rasm)."
    },
    "ru": {
        "choose_lang": "Выберите язык:",
        "main_menu": "📋 Главное меню:",
        "balance": "💰 Баланс: {} USD",
        "deposit": "➕ Депозит",
        "withdraw": "💸 Вывод",
        "market": "💹 Рынок",
        "trade": "📊 Торговля",
        "help": "ℹ️ Помощь",
        "back": "⬅️ Назад",
        "home": "🏠 Главное меню",
        "admin": "⚙️ Панель админа",
        "deposit_info": "Реквизиты для депозита предоставит админ. После перевода пришлите скриншот и сообщите администратору.",
        "withdraw_request_received": "✅ Ваш запрос принят. Админ скоро рассмотрит.",
        "withdraw_ask_details": "Пожалуйста, отправьте данные и сумму для вывода (например: `8600123456789012 50000`).",
        "withdraw_admin_notify": "💳 Новый запрос на вывод!\n👤 User: {}\nВалюта: {}\nДанные: {}\nСумма: {}\nВремя: {}",
        "trade_start_choose": "Выберите актив для торговли:",
        "trade_time_choose": "Выберите время (Short/ Middle/ Long):",
        "trade_direction_choose": "Выберите прогноз: ⬆️ / ⬇️ / ➖",
        "trade_in_progress": "⏳ Сделка выполняется... результат будет позже.",
        "trade_result_win": "🎉 Вы выиграли! {} USD добавлено на баланс.",
        "trade_result_lose": "😔 Вы проиграли. {} USD списано с баланса.",
        "invalid_format": "❌ Неверный формат. Пожалуйста, следуйте инструкции.",
        "min_deposit": "Мин депозит: 15 USD, Макс: 3000 USD.",
        "upload_screenshot": "Пожалуйста, отправьте скриншот платежа (картинку)."
    },
    "en": {
        "choose_lang": "Choose language:",
        "main_menu": "📋 Main menu:",
        "balance": "💰 Balance: {} USD",
        "deposit": "➕ Deposit",
        "withdraw": "💸 Withdraw",
        "market": "💹 Market",
        "trade": "📊 Trade",
        "help": "ℹ️ Help",
        "back": "⬅️ Back",
        "home": "🏠 Home",
        "admin": "⚙️ Admin panel",
        "deposit_info": "Deposit details will be provided by admin. After transfer, send screenshot and notify admin.",
        "withdraw_request_received": "✅ Your request received. Admin will review soon.",
        "withdraw_ask_details": "Please send withdraw details and amount (e.g.: `8600123456789012 50000`).",
        "withdraw_admin_notify": "💳 New withdraw request!\n👤 User: {}\nCurrency: {}\nDetails: {}\nAmount: {}\nTime: {}",
        "trade_start_choose": "Choose asset to trade:",
        "trade_time_choose": "Choose time (Short/ Middle/ Long):",
        "trade_direction_choose": "Choose prediction: ⬆️ / ⬇️ / ➖",
        "trade_in_progress": "⏳ Trade in progress... result will be announced later.",
        "trade_result_win": "🎉 You won! {} USD added to your balance.",
        "trade_result_lose": "😔 You lost. {} USD deducted from your balance.",
        "invalid_format": "❌ Invalid format. Please follow instructions.",
        "min_deposit": "Min deposit: 15 USD, Max: 3000 USD.",
        "upload_screenshot": "Please upload payment screenshot (image)."
    }
}

# -----------------------------
# DATABASE: SQLite init
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    # users table: user_id, lang, name, surname, birthday, email, login, password, balance, blocked
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'uz',
        name TEXT,
        surname TEXT,
        birthday TEXT,
        email TEXT,
        login TEXT,
        password TEXT,
        balance REAL DEFAULT 0,
        blocked INTEGER DEFAULT 0
    )''')
    # transactions: id, user_id, type, amount, details, timestamp
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        details TEXT,
        ts TEXT
    )''')
    # prices: name, value, ts
    c.execute('''CREATE TABLE IF NOT EXISTS prices (
        name TEXT PRIMARY KEY,
        value REAL,
        ts TEXT
    )''')
    # trades: id, user_id, asset, timeframe, direction, amount, result (pending/win/lose), ts
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        asset TEXT,
        timeframe TEXT,
        direction TEXT,
        amount REAL,
        result TEXT,
        ts TEXT
    )''')
    # withdraws: json backup (optional)
    conn.commit()
    return conn, c

conn, cur = init_db()

# -----------------------------
# Helper DB functions
# -----------------------------
def ensure_user_row(user_id, lang='uz'):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (user_id, lang, balance) VALUES (?, ?, ?)", (user_id, lang, 0.0))
        conn.commit()

def set_user_lang(user_id, lang):
    cur.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id)); conn.commit()

def get_user_row(user_id):
    cur.execute("SELECT user_id, lang, name, surname, birthday, email, login, password, balance, blocked FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()

def add_transaction(user_id, ttype, amount, details="-"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO transactions (user_id, type, amount, details, ts) VALUES (?, ?, ?, ?, ?)", (user_id, ttype, amount, details, ts))
    conn.commit()

def update_balance(user_id, new_balance):
    cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, user_id))
    conn.commit()

def change_balance_delta(user_id, delta):
    row = get_user_row(user_id)
    if not row:
        ensure_user_row(user_id)
        row = get_user_row(user_id)
    balance = row[8] + delta
    cur.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, user_id))
    conn.commit()
    add_transaction(user_id, "balance_change", delta, "admin/ trade result")
    return balance

def save_price(name, value):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT OR REPLACE INTO prices (name, value, ts) VALUES (?, ?, ?)", (name, value, ts))
    conn.commit()

def get_price(name):
    cur.execute("SELECT value FROM prices WHERE name=?", (name,))
    r = cur.fetchone()
    return r[0] if r else None

def add_trade(user_id, asset, timeframe, direction, amount):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO trades (user_id, asset, timeframe, direction, amount, result, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, asset, timeframe, direction, amount, "pending", ts))
    conn.commit()
    return cur.lastrowid

def set_trade_result(trade_id, result):
    cur.execute("UPDATE trades SET result=? WHERE id=?", (result, trade_id))
    conn.commit()

# -----------------------------
# Price updater thread (APIs)
# - Cryptos: Binance (BTCUSDT, ETHUSDT)
# - Stocks/Gold/Oil: yfinance fallback (we try metals.live or yfinance)
# - Currency: exchangerate.host
# -----------------------------
ASSETS_LIST = [
    "BTC/USDT", "ETH/USDT", "GOLD/USD", "SILVER/USD", "OIL/BRNT", "EUR/USD", "USD/UZS", "TESLA", "APPLE", "S&P500"
]

def fetch_and_save_prices():
    while True:
        try:
            # Crypto via Binance
            try:
                r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5).json()
                btc = float(r.get("price", 0))
                save_price("BTC/USDT", btc)
            except Exception:
                pass
            try:
                r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", timeout=5).json()
                eth = float(r.get("price", 0))
                save_price("ETH/USDT", eth)
            except Exception:
                pass

            # Gold/Silver via metals.live or fallback random
            try:
                r = requests.get("https://api.metals.live/v1/spot", timeout=6).json()  # returns [gold, silver, platinum,...]
                if isinstance(r, list) and len(r) >= 2:
                    save_price("GOLD/USD", float(r[0]))
                    save_price("SILVER/USD", float(r[1]))
                else:
                    raise Exception("metals.live invalid")
            except Exception:
                # fallback small random walk
                prev = get_price("GOLD/USD") or 1900.0
                new = prev + random.uniform(-2, 2)
                save_price("GOLD/USD", round(new, 2))
                prevs = get_price("SILVER/USD") or 24.0
                save_price("SILVER/USD", round(prevs + random.uniform(-0.2, 0.2), 3))

            # Oil (use Yahoo via stooq or api-ninjas if API key present)
            try:
                if API_NINJAS_KEY:
                    r = requests.get("https://api.api-ninjas.com/v1/oilprice", headers={"X-Api-Key": API_NINJAS_KEY}, timeout=6).json()
                    save_price("OIL/BRNT", float(r.get("price", 0)))
                else:
                    # cheap fallback: random around 80
                    prev = get_price("OIL/BRNT") or 80.0
                    new = prev + random.uniform(-1.0, 1.0)
                    save_price("OIL/BRNT", round(new, 2))
            except Exception:
                prev = get_price("OIL/BRNT") or 80.0
                save_price("OIL/BRNT", round(prev + random.uniform(-1, 1), 2))

            # Forex (USD/UZS via exchangerate.host)
            try:
                r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=UZS,EUR", timeout=6).json()
                rates = r.get("rates", {})
                if rates.get("UZS"):
                    save_price("USD/UZS", float(rates["UZS"]))
                if rates.get("EUR"):
                    save_price("EUR/USD", 1 / float(rates["EUR"]))  # approximate EUR/USD by base
            except Exception:
                # fallback random small change
                prev = get_price("USD/UZS") or 12500.0
                save_price("USD/UZS", round(prev + random.uniform(-10, 10), 2))

            # Stocks (Tesla, Apple) via Yahoo (simple)
            try:
                # Using Yahoo finance unofficial JSON via query1.finance.yahoo.com not advised; fallback random walk
                prev = get_price("TESLA") or 250.0
                save_price("TESLA", round(prev + random.uniform(-3, 3), 2))
                prev2 = get_price("APPLE") or 150.0
                save_price("APPLE", round(prev2 + random.uniform(-2, 2), 2))
            except Exception:
                pass

            # S&P500
            prev = get_price("S&P500") or 4300.0
            save_price("S&P500", round(prev + random.uniform(-5, 5), 2))

            # print debug
            # print("Prices updated:", datetime.now())
        except Exception as e:
            print("Price updater error:", e)
            traceback.print_exc()
        time.sleep(PRICE_UPDATE_INTERVAL)

# Start price updater thread as daemon
t = threading.Thread(target=fetch_and_save_prices, daemon=True)
t.start()

# -----------------------------
# Keyboards helpers
# -----------------------------
def main_menu_kb(lang):
    t = TEXTS[lang]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(t["balance"].split()[0] if False else "💰 Balans", "➕ Depozit")
    kb.row("💸 Pul yechish", "💹 Bozor")
    kb.row("📊 Savdo", "ℹ️ Yordam")
    kb.row("🌐 Tilni tanlash")
    # ADMIN button
    if ADMIN_ID:
        kb.row("⚙️ Admin")
    return kb

def lang_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇺🇿 O‘zbekcha", "🇷🇺 Русский", "🇬🇧 English")
    return kb

def back_home_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(TEXTS[lang]["back"], TEXTS[lang]["home"])
    return kb

# -----------------------------
# Start handler & language
# -----------------------------
@bot.message_handler(commands=["start"])
def cmd_start(m):
    ensure_user_row(m.chat.id)
    bot.send_message(m.chat.id, TEXTS["uz"]["choose_lang"], reply_markup=lang_kb())
    # ADMIN: user registered -> send to admin channel (so admin can track)
    try:
        user = m.from_user
        info = f"🆕 Start: {user.id} | @{user.username or 'nousername'} | {user.full_name}"
        bot.send_message(ADMIN_CHANNEL_ID, info)
    except Exception:
        pass

@bot.message_handler(func=lambda msg: msg.text in ["🇺🇿 O‘zbekcha", "🇷🇺 Русский", "🇬🇧 English"])
def set_lang_handler(m):
    if "O‘zbekcha" in m.text:
        lang='uz'
    elif "Русский" in m.text:
        lang='ru'
    else:
        lang='en'
    ensure_user_row(m.chat.id, lang)
    set_user_lang(m.chat.id, lang)
    bot.send_message(m.chat.id, TEXTS[lang]["main_menu"], reply_markup=main_menu_kb(lang))

# -----------------------------
# Main message handler
# -----------------------------
@bot.message_handler(func=lambda m: True)
def all_messages(m):
    try:
        row = get_user_row(m.chat.id)
        if not row:
            ensure_user_row(m.chat.id)
            row = get_user_row(m.chat.id)
        user_id, lang, *_rest = row[0], row[1], row[2:]
        if row[9] == 1 and user_id != ADMIN_ID:
            return bot.send_message(m.chat.id, "❌ Siz bloklangansiz. Admin bilan bog'laning.")

        text = m.text.strip()

        # BALANCE
        if text in ["💰 Balans", "💰 Баланс", "💰 Balance"]:
            row = get_user_row(m.chat.id)
            bal = row[8]
            bot.send_message(m.chat.id, TEXTS[lang]["balance"].format(round(bal,2)), reply_markup=back_home_kb(lang))
            return

        # DEPOSIT
        if text in ["➕ Depozit", "➕ Депозит", "➕ Deposit"]:
            bot.send_message(m.chat.id, TEXTS[lang]["deposit_info"] + "\n" + TEXTS[lang]["min_deposit"], reply_markup=back_home_kb(lang))
            # Offer buttons to choose deposit currency
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("USD", "UZS", "CRYPTO")
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, "Depozit valyutasini tanlang:", reply_markup=kb)
            return

        if text in ["USD", "UZS", "CRYPTO"]:
            # Ask amount
            bot.send_message(m.chat.id, "Iltimos summani USD da yozing (masalan: 100):", reply_markup=back_home_kb(lang))
            bot.register_next_step_handler(m, handle_deposit_amount, text)
            return

        # WITHDRAW
        if text in ["💸 Pul yechish", "💸 Вывод", "💸 Withdraw"]:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("UZCARD", "HUMO", "VISA/MASTERCARD", "CRYPTO")
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, "Pul yechish turini tanlang:", reply_markup=kb)
            return

        if text in ["UZCARD", "HUMO", "VISA/MASTERCARD", "CRYPTO"]:
            bot.send_message(m.chat.id, TEXTS[lang]["withdraw_ask_details"], reply_markup=back_home_kb(lang))
            bot.register_next_step_handler(m, handle_withdraw_details, text)
            return

        # MARKET
        if text in ["💹 Bozor", "💹 Рынок", "💹 Market", "📊 Bozor", "📊 Рынок", "📊 Market"]:
            # show assets as keyboard (from ASSETS_LIST)
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            # use ASSETS_LIST from price updater
            for asset in ASSETS_LIST:
                kb.add(asset)
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, TEXTS[lang]["trade_start_choose"], reply_markup=kb)
            return

        # Asset price display when asset name matches
        if text in ASSETS_LIST:
            price = get_price(text)
            if price is None:
                bot.send_message(m.chat.id, f"{text} narxi hozircha mavjud emas.", reply_markup=back_home_kb(lang))
            else:
                bot.send_message(m.chat.id, f"{text}: {price}", reply_markup=back_home_kb(lang))
            return

        # TRADE
        if text in ["📊 Savdo", "📊 Торговля", "📊 Trade"]:
            # show assets
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for asset in ASSETS_LIST:
                kb.add(asset)
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, TEXTS[lang]["trade_start_choose"], reply_markup=kb)
            return

        # If picked asset for trade
        if text in ASSETS_LIST:
            # store in memory for this chat
            if not hasattr(bot, "CTX"): bot.CTX = {}
            bot.CTX[m.chat.id] = {"asset": text}
            # time selection: Short/Middle/Long but shown labels
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("Short (10s)", "Middle (20s)", "Long (50s)")
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, TEXTS[lang]["trade_time_choose"], reply_markup=kb)
            return

        if text in ["Short (10s)", "Middle (20s)", "Long (50s)"]:
            if not hasattr(bot, "CTX") or m.chat.id not in bot.CTX or "asset" not in bot.CTX[m.chat.id]:
                bot.send_message(m.chat.id, "Iltimos avval aktiv tanlang.", reply_markup=back_home_kb(lang))
                return
            bot.CTX[m.chat.id]["time"] = text
            # choose direction
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("⬆️ Tepaga", "⬇️ Pastga", "➖ O'zgarmaydi")
            kb.add(TEXTS[lang]["back"])
            bot.send_message(m.chat.id, TEXTS[lang]["trade_direction_choose"], reply_markup=kb)
            return

        if text in ["⬆️ Tepaga", "⬇️ Pastga", "➖ O'zgarmaydi"]:
            ctx = getattr(bot, "CTX", {}).get(m.chat.id)
            if not ctx:
                bot.send_message(m.chat.id, "Iltimos avval aktiv tanlang.", reply_markup=back_home_kb(lang))
                return
            asset = ctx.get("asset")
            timeframe = ctx.get("time")
            direction = text
            # Ask bet amount
            bot.send_message(m.chat.id, "Iltimos tikish summasini USD da yozing (masalan: 100):", reply_markup=back_home_kb(lang))
            bot.register_next_step_handler(m, handle_trade_amount, asset, timeframe, direction)
            return

        # Admin panel entry
        if text in ["⚙️ Admin", "/admin"] and m.chat.id == ADMIN_ID:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("📋 Foydalanuvchilar", "📥 Yechish so'rovlari")
            kb.add("/withdraws", "/trades")
            bot.send_message(m.chat.id, "Admin panel", reply_markup=kb)
            return

        # Back default
        bot.send_message(m.chat.id, TEXTS[lang]["invalid_format"], reply_markup=back_home_kb(lang))
    except Exception as e:
        traceback.print_exc()
        bot.send_message(ADMIN_ID, f"Handler xatolik: {e}")

# -----------------------------
# Deposit handlers
# -----------------------------
def handle_deposit_amount(message, currency):
    try:
        user_id = message.chat.id
        text = message.text.strip()
        lang = get_user_row(user_id)[1]
        # parse amount
        try:
            amount = float(text)
        except:
            return bot.send_message(user_id, TEXTS[lang]["invalid_format"], reply_markup=back_home_kb(lang))
        # check bounds in USD
        if amount < 15:
            return bot.send_message(user_id, "Minimal depozit {}.".format(TEXTS[lang]["min_deposit"]), reply_markup=back_home_kb(lang))
        if amount > 3000:
            return bot.send_message(user_id, "Maksimal depozit 3000 USD", reply_markup=back_home_kb(lang))
        # Ask screenshot
        bot.send_message(user_id, TEXTS[lang]["upload_screenshot"])
        # register next step to receive photo
        bot.register_next_step_handler(message, handle_deposit_screenshot, currency, amount)
    except Exception as e:
        traceback.print_exc()

def handle_deposit_screenshot(message, currency, amount):
    try:
        user_id = message.chat.id
        lang = get_user_row(user_id)[1]
        # Save photo file_id if provided
        photo_id = None
        if message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            # Save to DB as transaction pending admin confirmation
            add_transaction(user_id, "deposit_request", amount, f"{currency} | screenshot:{photo_id}")
            # Notify admin with user and details
            bot.send_message(ADMIN_CHANNEL_ID, f"💳 Depozit so'rovi: user {user_id} | {currency} | {amount} USD | screenshot_id:{photo_id}")
            bot.send_message(user_id, "✅ Depozit so'rovingiz qabul qilindi. Admin tasdiqlaydi.", reply_markup=back_home_kb(lang))
        else:
            bot.send_message(user_id, "Iltimos rasmini yuboring (photo).", reply_markup=back_home_kb(lang))
    except Exception as e:
        traceback.print_exc()

# -----------------------------
# Withdraw handlers
# -----------------------------
def handle_withdraw_details(message, withdraw_type):
    try:
        user_id = message.chat.id
        lang = get_user_row(user_id)[1]
        parts = message.text.strip().split()
        if len(parts) < 2:
            return bot.send_message(user_id, TEXTS[lang]["invalid_format"], reply_markup=back_home_kb(lang))
        details = " ".join(parts[:-1])
        try:
            amount = float(parts[-1])
        except:
            return bot.send_message(user_id, TEXTS[lang]["invalid_format"], reply_markup=back_home_kb(lang))
        # check balance
        user_row = get_user_row(user_id)
        bal = user_row[8]
        if amount > bal:
            return bot.send_message(user_id, "❌ Balansingiz yetarli emas.", reply_markup=back_home_kb(lang))
        # deduct immediately or keep pending? We'll mark pending and deduct when approved -> For realism we deduct pending amount
        new_bal = bal - amount
        cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id)); conn.commit()
        add_transaction(user_id, "withdraw_request", amount, f"{withdraw_type} | {details}")
        # Save withdraw request into file for admin list
        withdraws = load_withdraws()
        uid = str(user_id)
        if uid not in withdraws: withdraws[uid] = []
        withdraws[uid].append({"type": withdraw_type, "details": details, "amount": amount, "status": "pending", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_withdraws(withdraws)
        bot.send_message(user_id, TEXTS[lang]["withdraw_request_received"], reply_markup=back_home_kb(lang))
        # notify admin
        bot.send_message(ADMIN_CHANNEL_ID, TEXTS[lang]["withdraw_admin_notify"].format(user_id, withdraw_type, details, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except Exception as e:
        traceback.print_exc()

def load_withdraws():
    try:
        if os.path.exists(WITHDRAW_FILE):
            with open(WITHDRAW_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_withdraws(d):
    try:
        with open(WITHDRAW_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except:
        pass

# ADMIN commands for withdraws
@bot.message_handler(commands=["withdraws"])
def admin_show_withdraws(m):
    if m.chat.id != ADMIN_ID:
        return
    withdraws = load_withdraws()
    text = ""
    for uid, arr in withdraws.items():
        for idx, it in enumerate(arr):
            text += f"User: {uid} | idx: {idx+1}\nType: {it['type']} | Amount: {it['amount']} | Status: {it['status']} | Time: {it['time']}\nDetails: {it['details']}\n\n"
    if not text:
        bot.send_message(ADMIN_ID, "So'rovlar topilmadi.")
    else:
        bot.send_message(ADMIN_ID, "📋 Withdraws:\n\n" + text)

@bot.message_handler(commands=["approve_withdraw"])
def admin_approve_withdraw(m):
    # usage: /approve_withdraw user_id idx
    if m.chat.id != ADMIN_ID:
        return
    parts = m.text.split()
    if len(parts) < 3:
        bot.send_message(ADMIN_ID, "Foydalanish: /approve_withdraw user_id idx")
        return
    uid = parts[1]; idx = int(parts[2]) - 1
    withdraws = load_withdraws()
    if uid not in withdraws or idx < 0 or idx >= len(withdraws[uid]):
        bot.send_message(ADMIN_ID, "So'rov topilmadi.")
        return
    withdraws[uid][idx]['status'] = 'approved'
    save_withdraws(withdraws)
    bot.send_message(ADMIN_ID, "✅ Approved")
    try:
        bot.send_message(int(uid), "✅ Sizning pul yechish so'rovingiz admin tomonidan TASDIQLANDI.")
    except:
        pass

@bot.message_handler(commands=["reject_withdraw"])
def admin_reject_withdraw(m):
    # usage: /reject_withdraw user_id idx
    if m.chat.id != ADMIN_ID:
        return
    parts = m.text.split()
    if len(parts) < 3:
        bot.send_message(ADMIN_ID, "Foydalanish: /reject_withdraw user_id idx")
        return
    uid = parts[1]; idx = int(parts[2]) - 1
    withdraws = load_withdraws()
    if uid not in withdraws or idx < 0 or idx >= len(withdraws[uid]):
        bot.send_message(ADMIN_ID, "So'rov topilmadi.")
        return
    item = withdraws[uid][idx]
    withdraws[uid][idx]['status'] = 'rejected'
    save_withdraws(withdraws)
    bot.send_message(ADMIN_ID, "❌ Rejected")
    # refund amount
    try:
        amount = float(item['amount'])
        user_row = get_user_row(int(uid))
        if user_row:
            new_bal = user_row[8] + amount
            cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, int(uid))); conn.commit()
            add_transaction(int(uid), "withdraw_rejected_refund", amount, "refund after reject")
            bot.send_message(int(uid), f"💰 {amount} USD balansingizga qaytarildi (so'rov rad qilindi).")
    except Exception:
        pass

# -----------------------------
# Trade handlers
# -----------------------------
def handle_trade_amount(message, asset, timeframe, direction):
    try:
        user_id = message.chat.id
        lang = get_user_row(user_id)[1]
        try:
            amount = float(message.text.strip())
        except:
            return bot.send_message(user_id, TEXTS[lang]["invalid_format"], reply_markup=back_home_kb(lang))
        # check balance
        row = get_user_row(user_id)
        bal = row[8]
        if amount > bal:
            return bot.send_message(user_id, "❌ Balansingiz yetarli emas.", reply_markup=back_home_kb(lang))
        # deduct amount immediately (simulate locked)
        new_bal = bal - amount
        cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, user_id)); conn.commit()
        add_transaction(user_id, "trade_start", amount, f"{asset}|{timeframe}|{direction}")
        # create trade row pending
        trade_id = add_trade(user_id, asset, timeframe, direction, amount)
        # simulate real-time ticks and notify admin to /win or /lose optionally
        # For realism: we simulate price movements and determine outcome probabilistically (80% win)
        # But also allow admin to override with /win or /lose commands for trade_id
        bot.send_message(user_id, TEXTS[lang]["trade_in_progress"])
        # simulate ticks with per-second messages matching timeframe (10s/20s/50s)
        secs = 10 if "Short" in timeframe else (20 if "Middle" in timeframe else 50)
        # To avoid flooding, we will send summary ticks every second
        price = get_price(asset) or 100.0
        ticks = []
        for i in range(secs):
            # random walk
            step = random.uniform(-0.6, 0.6)
            price += step
            ticks.append(price)
            # send every second (synchronous sleep)
            try:
                bot.send_message(user_id, f"{i+1}s: {round(price,4)} {'⬆️' if step>0 else ('⬇️' if step<0 else '➖')}")
            except Exception:
                pass
            time.sleep(1)
        # determine outcome: 80% win default
        is_win = random.random() < 0.8
        # compute payout multiplier: Short x2, Middle x4, Long x8 (as requested)
        multiplier = 2 if secs == 10 else (4 if secs == 20 else 8)
        if is_win:
            win_amount = amount * (multiplier - 1)  # profit (so returning stake + profit)
            # Add stake back + profit
            new_bal2 = new_bal + amount + win_amount
            cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal2, user_id)); conn.commit()
            add_transaction(user_id, "trade_win", win_amount, f"trade_id:{trade_id}")
            set_trade_result(trade_id, "win")
            bot.send_message(user_id, TEXTS[lang]["trade_result_win"].format(round(win_amount,2)), reply_markup=back_home_kb(lang))
            # notify admin
            bot.send_message(ADMIN_CHANNEL_ID, f"Trade #{trade_id} user {user_id} WIN +{round(win_amount,2)}")
        else:
            # loss: stake already deducted -> no refund
            set_trade_result(trade_id, "lose")
            add_transaction(user_id, "trade_lose", -amount, f"trade_id:{trade_id}")
            bot.send_message(user_id, TEXTS[lang]["trade_result_lose"].format(round(amount,2)), reply_markup=back_home_kb(lang))
            bot.send_message(ADMIN_CHANNEL_ID, f"Trade #{trade_id} user {user_id} LOSE -{round(amount,2)}")
    except Exception as e:
        traceback.print_exc()
        bot.send_message(ADMIN_CHANNEL_ID, f"Trade handler error: {e}")

# Admin commands to force win/lose on a trade
@bot.message_handler(commands=["win"])
def admin_win(m):
    # usage: /win trade_id
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 2:
        return bot.send_message(ADMIN_ID, "Foydalanish: /win trade_id")
    try:
        tid = int(parts[1])
    except:
        return bot.send_message(ADMIN_ID, "trade_id raqam bo'lishi kerak")
    # fetch trade
    cur.execute("SELECT id, user_id, amount, timeframe FROM trades WHERE id=?", (tid,))
    tr = cur.fetchone()
    if not tr:
        return bot.send_message(ADMIN_ID, "Trade topilmadi")
    uid = tr[1]; amount = tr[2]; timeframe = tr[3]
    secs = 10 if "Short" in timeframe else (20 if "Middle" in timeframe else 50)
    multiplier = 2 if secs==10 else (4 if secs==20 else 8)
    win_amount = amount * (multiplier - 1)
    # credit
    user_row = get_user_row(uid)
    new_bal = user_row[8] + amount + win_amount
    cur.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, uid)); conn.commit()
    set_trade_result(tid, "win")
    add_transaction(uid, "trade_win_admin", win_amount, f"admin_forced_win {tid}")
    bot.send_message(uid, TEXTS[user_row[1]]["trade_result_win"].format(round(win_amount,2)))
    bot.send_message(ADMIN_ID, f"Trade {tid} set to WIN by admin.")

@bot.message_handler(commands=["lose"])
def admin_lose(m):
    # usage: /lose trade_id
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 2:
        return bot.send_message(ADMIN_ID, "Foydalanish: /lose trade_id")
    try:
        tid = int(parts[1])
    except:
        return bot.send_message(ADMIN_ID, "trade_id raqam bo'lishi kerak")
    cur.execute("SELECT id, user_id, amount, timeframe FROM trades WHERE id=?", (tid,))
    tr = cur.fetchone()
    if not tr:
        return bot.send_message(ADMIN_ID, "Trade topilmadi")
    uid = tr[1]; amount = tr[2]
    # already deducted at start; nothing to do but mark lose
    set_trade_result(tid, "lose")
    add_transaction(uid, "trade_lose_admin", -amount, f"admin_forced_lose {tid}")
    bot.send_message(uid, "❌ Trade admin tomonidan yo'qotish deb belgilandi.")
    bot.send_message(ADMIN_ID, f"Trade {tid} set to LOSE by admin.")

# -----------------------------
# Admin tools: list trades, users, add/sub balance, block/unblock
# -----------------------------
@bot.message_handler(commands=["trades"])
def admin_list_trades(m):
    if m.chat.id != ADMIN_ID: return
    cur.execute("SELECT id, user_id, asset, timeframe, amount, result, ts FROM trades ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    if not rows:
        bot.send_message(ADMIN_ID, "Trade topilmadi")
        return
    text = ""
    for r in rows:
        text += f"#{r[0]} | user:{r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]}\n"
    bot.send_message(ADMIN_ID, text)

@bot.message_handler(commands=["users"])
def admin_list_users(m):
    if m.chat.id != ADMIN_ID: return
    cur.execute("SELECT user_id, balance, blocked FROM users")
    rows = cur.fetchall()
    text = ""
    for r in rows:
        status = "blocked" if r[2] else "active"
        text += f"{r[0]} | balance: {r[1]} | {status}\n"
    bot.send_message(ADMIN_ID, text)

@bot.message_handler(commands=["addbal"])
def admin_add_balance(m):
    # usage: /addbal user_id amount
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 3: return bot.send_message(ADMIN_ID, "Usage: /addbal user_id amount")
    try:
        uid = int(parts[1]); amt = float(parts[2])
    except:
        return bot.send_message(ADMIN_ID, "Format xato")
    row = get_user_row(uid)
    if not row:
        ensure_user_row(uid)
    change_balance_delta(uid, amt)
    bot.send_message(ADMIN_ID, f"{amt} qo'shildi user {uid}")

@bot.message_handler(commands=["subbal"])
def admin_sub_balance(m):
    # usage: /subbal user_id amount
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 3: return bot.send_message(ADMIN_ID, "Usage: /subbal user_id amount")
    try:
        uid = int(parts[1]); amt = float(parts[2])
    except:
        return bot.send_message(ADMIN_ID, "Format xato")
    change_balance_delta(uid, -amt)
    bot.send_message(ADMIN_ID, f"{amt} ayirildi user {uid}")

@bot.message_handler(commands=["block"])
def admin_block(m):
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 2: return bot.send_message(ADMIN_ID, "Usage: /block user_id")
    try:
        uid = int(parts[1])
    except:
        return bot.send_message(ADMIN_ID, "ID xato")
    cur.execute("UPDATE users SET blocked=1 WHERE user_id=?", (uid,)); conn.commit()
    bot.send_message(ADMIN_ID, f"{uid} block qilindi")

@bot.message_handler(commands=["unblock"])
def admin_unblock(m):
    if m.chat.id != ADMIN_ID: return
    parts = m.text.split()
    if len(parts) < 2: return bot.send_message(ADMIN_ID, "Usage: /unblock user_id")
    try:
        uid = int(parts[1])
    except:
        return bot.send_message(ADMIN_ID, "ID xato")
    cur.execute("UPDATE users SET blocked=0 WHERE user_id=?", (uid,)); conn.commit()
    bot.send_message(ADMIN_ID, f"{uid} unblock qilindi")

# -----------------------------
# Small util commands for users
# -----------------------------
@bot.message_handler(commands=["balance"])
def cmd_balance(m):
    row = get_user_row(m.chat.id)
    if not row:
        ensure_user_row(m.chat.id)
        row = get_user_row(m.chat.id)
    lang = row[1]
    bot.send_message(m.chat.id, TEXTS[lang]["balance"].format(round(row[8],2)), reply_markup=main_menu_kb(lang))

# -----------------------------
# Graceful run: ensure withdraw file exists
# -----------------------------
if not os.path.exists(WITHDRAW_FILE):
    save_withdraws({})

# -----------------------------
# Run polling with restart loop
# -----------------------------
def main():
    print("Bot ishga tushdi...")
    # Ensure price updater thread is running (started above)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout = 60)
        except Exception as e:
            print("Polling xatolik:", e)
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()