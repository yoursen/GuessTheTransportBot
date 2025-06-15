import logging
import json
import random
import os
import asyncio
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
    # Create an inline keyboard with a button to start the quiz
    keyboard = [[InlineKeyboardButton("Start Quiz", callback_data="start_quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Transport Quiz!\nI will send you a photo of a transport, and you must guess what it is. Press the button below to start!",
        reply_markup=reply_markup
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {'score': 0, 'asked': 0}
    await send_next_quiz(update.effective_chat.id, user_id, context)

async def send_next_quiz(chat_id, user_id, context):
    try:
        question = get_random_question()
        user_data[user_id]['current'] = question
        keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in question['options']]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Verify the photo file exists
        if not os.path.exists(question['photo']):
            logger.error(f"Photo file not found: {question['photo']}")
            raise FileNotFoundError(f"Photo file not found: {question['photo']}")
            
        with open(question['photo'], 'rb') as photo:
            await context.bot.send_photo(chat_id=chat_id, photo=photo, caption="What is this transport?", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in send_next_quiz: {str(e)}")
        keyboard = [[InlineKeyboardButton("Start new game", callback_data="start_quiz")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, there was an error loading the question. Please start a new game.",
            reply_markup=reply_markup
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Handle the start quiz button
    if query.data == "start_quiz":
        if user_id not in user_data:
            user_data[user_id] = {'score': 0, 'asked': 0}
        await send_next_quiz(query.message.chat_id, user_id, context)
        return
    
    # Check if user data exists or if we lost state due to server restart
    if user_id not in user_data or 'current' not in user_data[user_id]:
        # Server probably restarted and lost user state
        keyboard = [[InlineKeyboardButton("Start new game", callback_data="start_quiz")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(
            caption="Sorry, there was an error or the server restarted. Please start a new game.",
            reply_markup=reply_markup
        )
        return
    
    # Handle quiz answer buttons
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
    
    # Send next question automatically after a 2-second delay
    # This gives the user time to see the result of their answer
    chat_id = query.message.chat_id
    context.application.create_task(
        send_next_quiz_with_delay(chat_id, user_id, context)
    )

async def send_next_quiz_with_delay(chat_id, user_id, context):
    try:
        # Wait for 2 seconds before sending the next quiz item
        await asyncio.sleep(1)
        await send_next_quiz(chat_id, user_id, context)
    except Exception as e:
        logger.error(f"Error in send_next_quiz_with_delay: {str(e)}")
        try:
            keyboard = [[InlineKeyboardButton("Start new game", callback_data="start_quiz")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, there was an error sending the next question. Please start a new game.",
                reply_markup=reply_markup
            )
        except Exception as inner_e:
            logger.error(f"Failed to send error message: {str(inner_e)}")

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
