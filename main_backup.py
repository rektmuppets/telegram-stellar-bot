from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables
load_dotenv()

# Get bot token from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found in .env file")
    exit()

# Initialize bot
bot = Bot(token=BOT_TOKEN)
bot._defaults = {
    "parse_mode": ParseMode.HTML,
    "disable_web_page_preview": False,
    "protect_content": False,
    "link_preview": False
}

# Initialize dispatcher
dp = Dispatcher()

# Command to start the bot
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Hello! I'm your Stellar trading bot.")

# Command to show help message
@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - List available commands\n"
        "/balance - Check your balance\n"
        "/trade - Execute a trade"
    )

# Command to show mock balance
@dp.message(Command("balance"))
async def balance_command(message: Message):
    # Mock data for balance
    balance = {"XLM": 100.25, "USDC": 50.75}
    balance_text = "\n".join(f"{key}: {value}" for key, value in balance.items())
    await message.answer(f"Your balance:\n{balance_text}")

# Command to execute a mock trade
@dp.message(Command("trade"))
async def trade_command(message: Message):
    args = message.text.split()
    if len(args) != 4:
        await message.answer("Usage: /trade <source_token> <destination_token> <amount>")
        return

    source_token, destination_token, amount = args[1], args[2], args[3]
    try:
        amount = float(amount)
        # Mock trade execution
        await message.answer(
            f"Trade initiated:\n{amount} {source_token} -> {destination_token}"
        )
    except ValueError:
        await message.answer("Error: Amount must be a valid number.")

# Main entry point
async def main():
    print("Bot is starting...")
    try:
        # Register handlers
        dp.message.register(start_command)
        dp.message.register(help_command)
        dp.message.register(balance_command)
        dp.message.register(trade_command)

        # Start the bot
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Error during bot initialization: {e}")

if __name__ == "__main__":
    asyncio.run(main())
