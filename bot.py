import logging
import json
import random
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

QUIZ_FILE = 'quiz.json'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load quiz data from JSON
with open(QUIZ_FILE, 'r') as f:
    QUIZ = json.load(f)

user_data = {}
# Set to track active chat IDs for broadcast messages
active_chats = set()

load_dotenv()

# Bot owner Telegram ID (should be set in .env file)
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', '0'))  # Default to 0 if not set

def get_random_question(questions_asked=None):
    """
    Get a random question that hasn't been asked before.
    
    Args:
        questions_asked (list): List of indices of questions that have been asked already
        
    Returns:
        dict: A question that hasn't been asked yet, or None if all questions have been asked
    """
    if questions_asked is None:
        questions_asked = []
    
    # Get indices of questions that haven't been asked yet
    available_indices = [i for i in range(len(QUIZ)) if i not in questions_asked]
    
    # If all questions have been asked, return None
    if not available_indices:
        return None
    
    # Select a random question from the available ones
    question_index = random.choice(available_indices)
    question = QUIZ[question_index]
    
    # Return both the question and its index
    return question, question_index

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {'score': 0, 'asked': 0, 'questions_asked': []}
    
    # Add this chat to active chats
    active_chats.add(update.effective_chat.id)
    
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
        user_data[user_id] = {'score': 0, 'asked': 0, 'questions_asked': []}
    
    # Add this chat to active chats
    active_chats.add(update.effective_chat.id)
    
    await send_next_quiz(update.effective_chat.id, user_id, context)

async def send_next_quiz(chat_id, user_id, context):
    try:
        # Get a random question that hasn't been asked yet
        result = get_random_question(user_data[user_id].get('questions_asked', []))
        
        # If all questions have been asked
        if result is None:
            final_score = user_data[user_id]['score']
            total_questions = user_data[user_id]['asked']
            
            # Create a keyboard with a restart button
            keyboard = [[InlineKeyboardButton("Play Again", callback_data="restart_quiz")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎮 Quiz completed! 🎮\n\nYour final score: {final_score}/{total_questions}\n\nThank you for playing! Press the button below to play again.",
                reply_markup=reply_markup
            )
            return
        
        question, question_index = result
        
        # Add this question to the list of asked questions
        user_data[user_id]['questions_asked'].append(question_index)
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
            user_data[user_id] = {'score': 0, 'asked': 0, 'questions_asked': []}
        # Add this chat to active chats
        active_chats.add(query.message.chat_id)
        await send_next_quiz(query.message.chat_id, user_id, context)
        return
    
    # Handle the restart quiz button
    if query.data == "restart_quiz":
        user_data[user_id] = {'score': 0, 'asked': 0, 'questions_asked': []}
        # Add this chat to active chats
        active_chats.add(query.message.chat_id)
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

async def msg_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a message to all active chats. Only usable by the bot owner.
    Usage: /msgall Your message here
    """
    user_id = update.effective_user.id
    
    # Check if the command is being used by the bot owner
    if user_id != BOT_OWNER_ID:
        await update.message.reply_text("⛔ Sorry, this command is only available to the bot owner.")
        return
    
    # Get the message to broadcast
    if not context.args:
        await update.message.reply_text("Usage: /msgall Your message here")
        return
    
    broadcast_message = " ".join(context.args)
    
    # Count of successful deliveries
    success_count = 0
    
    # Send message to all active chats
    for chat_id in list(active_chats):
        try:
            await context.bot.send_message(chat_id=chat_id, text=broadcast_message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {str(e)}")
            # If we can't send a message, this chat is probably no longer active
            active_chats.discard(chat_id)
    
    await update.message.reply_text(f"✅ Message sent to {success_count} active chats.")

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    env = os.getenv('ENV', 'development')
    logger.info(f"Running in {env} mode")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('quiz', quiz))
    app.add_handler(CommandHandler('msgall', msg_all))
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
