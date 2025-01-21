from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
from dotenv import load_dotenv
import os
import asyncio
import logging
import sys

# Add the parent directory to the Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the .env file.")

# Initialize bot with updated settings
bot = Bot(
    token=BOT_TOKEN,
    session=AiohttpSession(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        protect_content=False
    )
)

# Initialize dispatcher
dp = Dispatcher()

# Import routers
from commands.general import router as general_router
from commands.stellar import router as stellar_router
from commands.verification import router as verification_router

# Include routers
dp.include_router(general_router)
dp.include_router(stellar_router)
dp.include_router(verification_router)

# Main entry point
async def main():
    try:
        logging.info("Bot is starting...")

        # Start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
