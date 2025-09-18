import logging
import random
import time
import asyncio
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)

# ============================
# ADMIN SOZLASHLARI
# ============================
TOKEN = "8311598762:AAF4U6q2wr8aJ0wfDvmkP3pe6_EAerZLLYA"  # ADMIN: Bot tokenini bu yerga yozing
ADMIN_ID = 123456789              # ADMIN: o'zingizning Telegram ID’ingizni yozing
ADMIN_CHANNEL = 2550798991     # ADMIN: foydalanuvchi malumotlari va screenshot yuboriladigan maxfiy kanal ID
# ============================

# LOG
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# FOYDALANUVCHILAR DB (oddiy dict, SQLite o‘rniga)
users = {}

# ======== YORDAMCHI FUNKSIYALAR ========
def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "balance": 100.0,
            "lang": "uz",
        }
    return users[user_id]

def set_lang(user_id, lang):
    users[user_id]["lang"] = lang

def update_balance(user_id, amount):
    users[user_id]["balance"] += amount

# ======== MENU FUNKSIYALARI ========
def main_menu(user_id):
    lang = users[user_id]["lang"]
    if lang == "uz":
        buttons = [
            ["💰 Balans", "➕ Depozit"],
            ["➖ Pul yechish", "🏪 Bozor"],
            ["📊 Savdo", "ℹ️ Yordam"],
            ["📢 Bizning kanal", "ℹ️ Ma'lumot"],
            ["🌐 Tilni tanlash"]
        ]
    elif lang == "ru":
        buttons = [
            ["💰 Баланс", "➕ Депозит"],
            ["➖ Вывод", "🏪 Рынок"],
            ["📊 Торговля", "ℹ️ Помощь"],
            ["📢 Наш канал", "ℹ️ Инфо"],
            ["🌐 Язык"]
        ]
    else:
        buttons = [
            ["💰 Balance", "➕ Deposit"],
            ["➖ Withdraw", "🏪 Market"],
            ["📊 Trade", "ℹ️ Help"],
            ["📢 Our Channel", "ℹ️ Info"],
            ["🌐 Language"]
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def back_menu(user_id):
    lang = users[user_id]["lang"]
    if lang == "uz":
        return ReplyKeyboardMarkup([["🔙 Orqaga", "🏠 Asosiy menyu"]], resize_keyboard=True)
    elif lang == "ru":
        return ReplyKeyboardMarkup([["🔙 Назад", "🏠 Главное меню"]], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["🔙 Back", "🏠 Main menu"]], resize_keyboard=True)

def language_menu():
    return ReplyKeyboardMarkup(
        [["🇺🇿 O‘zbekcha", "🇷🇺 Русский", "🇬🇧 English"]],
        resize_keyboard=True
    )

# ======== /start ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user = get_user(user_id)
    await update.message.reply_text(
        "🌐 Tilni tanlang | Choose language | Выберите язык",
        reply_markup=language_menu()
    )
    # ADMIN: foydalanuvchi start bosganda kanalga yozamiz
    await context.bot.send_message(
        ADMIN_CHANNEL,
        f"🆕 Yangi foydalanuvchi: {user_id}\nTil: {user['lang']}\nBalans: {user['balance']}$"
    )

# ======== HANDLER ========
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user = get_user(user_id)
    text = update.message.text
    lang = user["lang"]

    # LANGUAGE tanlash
    if text in ["🇺🇿 O‘zbekcha", "🇷🇺 Русский", "🇬🇧 English"]:
        if "O‘zbekcha" in text:
            set_lang(user_id, "uz")
        elif "Русский" in text:
            set_lang(user_id, "ru")
        else:
            set_lang(user_id, "en")
        await update.message.reply_text("✅ Til o‘zgartirildi!", reply_markup=main_menu(user_id))
        return

    # BACK
    if text in ["🔙 Orqaga", "🔙 Назад", "🔙 Back", "🏠 Asosiy menyu", "🏠 Главное меню", "🏠 Main menu"]:
        await update.message.reply_text("🏠", reply_markup=main_menu(user_id))
        return

    # BALANCE
    if text in ["💰 Balans", "💰 Баланс", "💰 Balance"]:
        await update.message.reply_text(
            f"💳 {user['balance']}$",
            reply_markup=back_menu(user_id)
        )
        return

    # DEPOSIT
    if text in ["➕ Depozit", "➕ Депозит", "➕ Deposit"]:
        buttons = [["💵 UZS", "💲 USD", "🪙 Crypto"], ["🔙 Orqaga"]]
        await update.message.reply_text("➕ Depozit turini tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    # WITHDRAW
    if text in ["➖ Pul yechish", "➖ Вывод", "➖ Withdraw"]:
        buttons = [["💵 UZCARD", "💳 HUMO"], ["💳 VISA", "💳 MasterCard"], ["🪙 Crypto"], ["🔙 Orqaga"]]
        await update.message.reply_text("➖ Pul yechish turini tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    # MARKET (faqat narxlar ko‘rsatadi)
    if text in ["🏪 Bozor", "🏪 Рынок", "🏪 Market"]:
        market_items = ["🥇 Oltin", "🛢 Neft", "💵 EUR/USD", "₿ BTC/USDT"]
        buttons = [[item] for item in market_items] + [["🔙 Orqaga"]]
        await update.message.reply_text("📦 Bozor:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    if text in ["🥇 Oltin", "🛢 Neft", "💵 EUR/USD", "₿ BTC/USDT"]:
        price = round(random.uniform(50, 500), 2)
        await update.message.reply_text(f"{text} narxi: {price}$", reply_markup=back_menu(user_id))
        return

    # TRADE
    if text in ["📊 Savdo", "📊 Торговля", "📊 Trade"]:
        items = ["🥇 Oltin", "🛢 Neft", "💵 EUR/USD", "₿ BTC/USDT"]
        buttons = [[item] for item in items] + [["🔙 Orqaga"]]
        await update.message.reply_text("📊 Savdo mahsulotini tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    if text in ["🥇 Oltin", "🛢 Neft", "💵 EUR/USD", "₿ BTC/USDT"]:
        buttons = [["Short", "Middle", "Long"], ["🔙 Orqaga"]]
        context.user_data["trade_item"] = text
        await update.message.reply_text("⏳ Vaqtni tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    if text in ["Short", "Middle", "Long"]:
        context.user_data["trade_time"] = text
        buttons = [["⬆️ Tepaga", "⬇️ Pastga", "➖ O‘zgarmaydi"], ["🔙 Orqaga"]]
        await update.message.reply_text("📈 Prognoz tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return

    if text in ["⬆️ Tepaga", "⬇️ Pastga", "➖ O‘zgarmaydi"]:
        item = context.user_data.get("trade_item", "❓")
        duration = context.user_data.get("trade_time", "Short")

        await update.message.reply_text(f"📊 Savdo boshlandi: {item}, {duration}")
        price = 100
        for i in range(5):  # qisqa simulyatsiya
            arrow = random.choice(["⬆️", "⬇️", "➖"])
            if arrow == "⬆️":
                price += random.randint(1, 5)
            elif arrow == "⬇️":
                price -= random.randint(1, 5)
            await update.message.reply_text(f"{i+1} soniya: {price} {arrow}")
            time.sleep(1)

        # 80% yutuq
        if random.random() < 0.8:
            win_amount = 10
            if duration == "Middle":
                win_amount = 20
            elif duration == "Long":
                win_amount = 40
            update_balance(user_id, win_amount)
            await update.message.reply_text(f"🎉 Yutuq! +{win_amount}$", reply_markup=back_menu(user_id))
        else:
            await update.message.reply_text("❌ Yutqazdingiz!", reply_markup=back_menu(user_id))
        return

    # HELP
    if text in ["ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"]:
        await update.message.reply_text("❓ Admin bilan bog‘laning: @username", reply_markup=back_menu(user_id))
        return

# ======== ADVERTISING JOB ========
async def send_ads(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(ADMIN_CHANNEL, "📢 Reklama: bizning botni sinab ko‘ring!")

# ======== MAIN ========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    # Har 3 soatda reklama
    job_queue = app.job_queue
    job_queue.run_repeating(send_ads, interval=10800, first=10)

    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
