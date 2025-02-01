import os
import requests
import base64
from io import BytesIO
from aiogram import types, Router
from aiogram.filters.command import Command
from aiogram.types import FSInputFile

router = Router()

# Load environment variables for API endpoints
CONNECT_WALLET_URL = os.getenv("CONNECT_WALLET_URL", "https://api.photonbot.xyz/connect-wallet")
LINK_WALLET_URL = os.getenv("LINK_WALLET_URL", "https://api.photonbot.xyz/link-wallet")

@router.message(Command("connectwallet"))
async def connect_wallet(message: types.Message):
    """
    Step 1: User initiates connection, QR is sent
    """
    try:
        response = requests.get(CONNECT_WALLET_URL)
        if response.status_code != 200:
            await message.reply(f"⚠️ Error generating QR code.")
            return
        
        qr_code_data = response.json().get("qrCode")
        qr_code_bytes = base64.b64decode(qr_code_data.split(",")[1])

        temp_file_path = "temp_qr.png"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(qr_code_bytes)

        qr_code_file = FSInputFile(temp_file_path, filename="walletconnect_qr.png")
        await message.answer_photo(qr_code_file, caption="Scan this QR code to connect your wallet.")

    except Exception as e:
        await message.reply(f"⚠️ An error occurred: {str(e)}")

@router.message(Command("register"))
async def register(message: types.Message):
    try:
        telegram_id = message.from_user.username or message.from_user.id
        wallet_address = "GABCDEF123456789"  # Replace with dynamic value
        session_topic = "mock-session-topic"  # Replace with dynamic value

        response = requests.post(LINK_WALLET_URL, json={
            "telegramID": telegram_id,
            "walletAddress": wallet_address,
            "sessionTopic": session_topic
        })

        if response.status_code == 200:
            await message.reply("✅ Wallet linked successfully!")
        else:
            await message.reply(f"⚠️ Failed to link wallet: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        await message.reply(f"⚠️ An error occurred: {str(e)}")


@router.message(Command("linkwallet"))
async def link_wallet(message: types.Message):
    """
    Check if the Telegram ID is linked to a wallet and session topic.
    """
    try:
        telegram_id = message.from_user.username  # Telegram username
        response = requests.get(f"{LINK_WALLET_URL}/{telegram_id}")

        if response.status_code == 200:
            linked_data = response.json()
            wallet_address = linked_data.get("walletAddress", "N/A")
            session_topic = linked_data.get("sessionTopic", "N/A")
            await message.reply(
                f"✅ Your wallet is linked successfully:\n"
                f"Wallet Address: {wallet_address}\n"
                f"Session Topic: {session_topic}"
            )
        else:
            await message.reply(f"⚠️ Failed to verify linkage. Server returned: {response.status_code}")
    except Exception as e:
        await message.reply(f"⚠️ An error occurred: {str(e)}")
