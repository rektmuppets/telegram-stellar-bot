# globals.py
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN or not isinstance(TELEGRAM_TOKEN, str):
    raise ValueError("TELEGRAM_TOKEN not found in .env or invalid.")

# Define globals
streaming_tasks = {}
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
shutdown_flag = asyncio.Event()  # Added for shutdown signaling