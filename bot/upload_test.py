from aiogram import Bot
from aiogram.types import FSInputFile
import asyncio

BOT_TOKEN = "8103083020:AAFsuQEYE8V55eD0Plb-b9Qd_-HVniwVVBQ"
CHAT_ID = 5014800072  # Replace with your numeric chat ID

async def send_test_image():
    bot = Bot(token=BOT_TOKEN)
    try:
        # Use FSInputFile for file uploads
        photo = FSInputFile("debug_qr.png")
        await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption="Test upload.")
        print("Image sent successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

asyncio.run(send_test_image())
