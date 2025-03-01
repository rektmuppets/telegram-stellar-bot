import asyncio
from aiogram import Bot, Dispatcher

async def main():
    bot = Bot(token="7248843412:AAG83psTqy9FhbkwavZoooQ-dYqnSSPq3Q8")  # Your hardcoded token
    dp = Dispatcher()  # No bot in constructor
    print("Bot instance:", bot)
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)  # Clear webhook state
    await dp.start_polling(bot)  # Pass bot here

if __name__ == "__main__":
    asyncio.run(main())