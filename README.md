# GuessTheTransportBot

GuessTheTransportBot is a simple Telegram bot game where users are shown a photo of a mode of transport and must guess what it is. The bot sends a photo and provides multiple-choice options for the user to select the correct answer.

## Play the Bot
[Start GuessTheTransportBot on Telegram](https://t.me/guess_transport_bot)

## Features
- Sends a photo of a transport (e.g., bus, train)
- Offers multiple-choice answers
- Checks if the user's answer is correct
- Provides feedback on the answer
- Designed for fun and learning about different types of transport
- Bot owner can broadcast messages to all active users

## How to Play
1. Start the bot in Telegram.
2. The bot will send you a photo of a transport.
3. Choose the correct answer from the options provided.
4. The bot will tell you if you are right or wrong and show the correct answer if needed.
5. Play again to guess more transports!

## Files
- `bot.py`: Main bot logic and Telegram integration
- `quiz.json`: Contains quiz questions, answers, and photo references
- `photos/`: Folder with images used in the quiz (e.g., `bus.jpg`, `train.jpg`)

## Requirements
- Python 3.x
- Telegram Bot API token
- Required Python packages (see `requirements.txt` for details)

## Setup
1. Clone this repository.
2. Create a `.env` file with the following configuration:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   BOT_OWNER_ID=your_telegram_id_here
   ENV=development
   ```
3. Make sure the `photos/` folder contains the required images.
4. Run the bot:
   ```bash
   python bot.py
   ```
5. Start chatting with your bot on Telegram!

## Admin Commands
- `/msgall [message]` - Sends a message to all active chats (only available to the bot owner)

## License
MIT License
