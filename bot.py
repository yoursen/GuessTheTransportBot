import logging
import json
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

QUIZ_FILE = 'quiz.json'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load quiz data from JSON
with open(QUIZ_FILE, 'r') as f:
    QUIZ = json.load(f)

user_data = {}

load_dotenv()

def get_random_question():
    return random.choice(QUIZ)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {'score': 0, 'asked': 0}
    await update.message.reply_text(
        "Welcome to the Transport Quiz!\nI will send you a photo of a transport, and you must guess what it is. Type /quiz to start!"
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = get_random_question()
    user_data[update.effective_user.id]['current'] = question
    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in question['options']]
    reply_markup = InlineKeyboardMarkup(keyboard)
    with open(question['photo'], 'rb') as photo:
        await update.message.reply_photo(photo=photo, caption="What is this transport?", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    question = user_data[user_id]['current']
    answer = question['answer']
    user_data[user_id]['asked'] += 1
    if query.data == answer:
        user_data[user_id]['score'] += 1
        text = "✅ Correct!"
    else:
        text = f"❌ Wrong! The correct answer was: {answer}"
    text += f"\nScore: {user_data[user_id]['score']}/{user_data[user_id]['asked']}"
    await query.edit_message_caption(caption=text)
    # Send next question
    await quiz(query, context)

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    env = os.getenv('ENV', 'development')
    logger.info(f"Running in {env} mode")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('quiz', quiz))
    app.add_handler(CallbackQueryHandler(button))
    if env != 'development':
        # Start webhook for production
        app.run_webhook(
            listen='0.0.0.0',
            port=int(os.environ.get('PORT', 10000)),
            webhook_url=os.environ.get('WEBHOOK_URL')
        )
    else:
        # Use polling for development
        app.run_polling()

if __name__ == '__main__':
    main()
