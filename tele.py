import subprocess
import sys
import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Install required packages
def install_packages():
    required_packages = [
        "python-telegram-bot==20.0",
        "typing-extensions",
        "exceptiongroup"
    ]

    for package in required_packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Run the installation of packages
install_packages()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define the bot token and owner ID
TOKEN = os.getenv('TOKEN', '7449574557:AAGcg6zL-hEVr7byvkVvCAIJPfBYtY-A8BQ')
OWNER_ID = int(os.getenv('OWNER_ID', '1696305024'))

# SQLite database setup
DB_NAME = 'chatbot.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        gender TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        user1_id INTEGER,
        user2_id INTEGER,
        message TEXT,
        FOREIGN KEY(user1_id) REFERENCES users(id),
        FOREIGN KEY(user2_id) REFERENCES users(id)
    )
    ''')
    conn.commit()
    conn.close()

def insert_user(user_id, username, gender):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO users (id, username, gender) VALUES (?, ?, ?)
    ''', (user_id, username, gender))
    conn.commit()
    conn.close()

def insert_conversation(user1_id, user2_id, message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO conversations (user1_id, user2_id, message) VALUES (?, ?, ?)
    ''', (user1_id, user2_id, message))
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Store user data
waiting_users = []
active_chats = {}
last_partner = {}
rematch_requests = {}
user_ids = {}
user_genders = {}

# Save user data to a file
def save_user_data_to_file():
    with open('user_data.txt', 'w') as file:
        for user_id in user_genders:
            username = user_ids.get(user_id, 'unknown')
            gender = user_genders[user_id]
            file.write(f"ID: {user_id}, Username: {username}, Gender: {gender}\n")

# Log message conversation
def log_conversation(user1_id: int, user2_id: int, message: str) -> None:
    insert_conversation(user1_id, user2_id, message)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        await update.message.reply_text('You are already in a chat. Use /skip to find a new partner or /stop to leave the chat.')
        return

    if user_id in waiting_users:
        await update.message.reply_text('You are already waiting for a chat partner.')
        return

    if user_id in user_genders:
        if waiting_users:
            partner_id = waiting_users.pop(0)
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            await update.message.reply_text(
                '🎉 You have been connected to a new chat! Use the following commands:\n'
                '/stop - Stop your current chat 🚪\n'
                '/skip - Skip to a new chat 🔄\n'
                '/rematch - Request a rematch with your last partner 🔁\n'
                '/share_usernames - Share your profile link 📤\n'
                '\nFor help, contact @Vi5h4u 🤖'
            )
            await context.bot.send_message(
                chat_id=partner_id,
                text='🎉 You have been connected to a new chat! Use the following commands:\n'
                     '/stop - Stop your current chat 🚪\n'
                     '/skip - Skip to a new chat 🔄\n'
                     '/rematch - Request a rematch with your last partner 🔁\n'
                     '/share_usernames - Share your profile link 📤\n'
                     '\nFor help, contact @Vi5h4u 🤖'
            )
        else:
            waiting_users.append(user_id)
            await update.message.reply_text(
                '⏳ You are now waiting for a chat partner. Use the following commands:\n'
                '/stop - Stop your current chat 🚪\n'
                '/skip - Skip to a new chat 🔄\n'
                '/rematch - Request a rematch with your last partner 🔁\n'
                '/share_usernames - Share your profile link 📤\n'
                '\nFor help, contact @Vi5h4u 🤖'
            )
    else:
        # Ask user for their gender
        keyboard = [
            [InlineKeyboardButton("Male 🧔", callback_data='male')],
            [InlineKeyboardButton("Female 👩", callback_data='female')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Please select your gender:', reply_markup=reply_markup)

# Gender selection callback
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    gender = query.data

    # Save gender
    user_genders[user_id] = gender
    user_ids[user_id] = (await context.bot.get_chat(user_id)).username
    insert_user(user_id, user_ids[user_id], gender)

    await query.answer()
    await query.edit_message_text(text=f"Gender set to {gender}. Use /start to begin. 🚀")

# Stop command
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text='Your chat partner has left the chat. 👋')
        await update.message.reply_text('You have left the chat. 👋')
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text('You are no longer waiting for a chat partner. 🚶')
    else:
        await update.message.reply_text('You are not connected to any chat.')

# Skip command
async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        last_partner[user_id] = partner_id
        last_partner[partner_id] = user_id
        await context.bot.send_message(chat_id=partner_id, text='Your chat partner has skipped to a new chat. 🆘\nUse /next to find another partner or /rematch to reconnect.')
        await update.message.reply_text('You have skipped to a new chat. 🔄\nUse /next to find another partner or /rematch to reconnect.')
    elif user_id in waiting_users:
        await update.message.reply_text('You are already waiting for a new chat.')
    else:
        await update.message.reply_text('You are not in a chat. Use /start to connect.')

# Rematch command
async def rematch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id not in last_partner:
        await update.message.reply_text('You have not skipped any chats recently. Use /start to connect with a new partner.')
        return

    partner_id = last_partner[user_id]

    if partner_id not in rematch_requests:
        rematch_requests[user_id] = True
        await update.message.reply_text('Rematch request sent. Waiting for your partner to confirm. ⏳')
        await context.bot.send_message(chat_id=partner_id, text='Your last partner has requested a rematch. Use /rematch to reconnect. 🔄')
    elif rematch_requests.get(partner_id):
        rematch_requests.pop(partner_id, None)
        last_partner.pop(user_id, None)
        last_partner.pop(partner_id, None)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=partner_id, text='Your partner has accepted the rematch request. You are now connected. 🎉')
        await update.message.reply_text('You are now connected with your last partner. 🎉')
    else:
        await update.message.reply_text('No rematch request available.')

# Next command
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        await update.message.reply_text('You are currently in a chat. Use /skip to leave the chat first.')
        return

    await start(update, context)

# Share usernames
async def share_usernames(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id not in active_chats:
        await update.message.reply_text('You need to be in a chat to share usernames.')
        return

    partner_id = active_chats[user_id]
    username1 = user_ids.get(user_id, 'unknown')
    username2 = user_ids.get(partner_id, 'unknown')

    await update.message.reply_text(f'Your username: @{username1}')
    await context.bot.send_message(chat_id=partner_id, text=f'Your partners username: @{username2}')

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id

    if user_id not in active_chats:
        await update.message.reply_text('You are not currently in a chat. Use /start to connect with a partner.')
        return

    partner_id = active_chats[user_id]
    message = update.message.text

    log_conversation(user_id, partner_id, message)
    await context.bot.send_message(chat_id=partner_id, text=message)

# Main function
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('skip', skip))
    application.add_handler(CommandHandler('rematch', rematch))
    application.add_handler(CommandHandler('next', next_chat))
    application.add_handler(CommandHandler('share_usernames', share_usernames))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
        
