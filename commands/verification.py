import requests
import base64
from io import BytesIO
from aiogram import types, Router
from aiogram.filters.command import Command
from aiogram.types import FSInputFile

router = Router()

@router.message(Command("connectwallet"))
async def connect_wallet(message: types.Message):
    """
    Fetch WalletConnect QR code from the Node.js server and send it to the user.
    """
    try:
        # Fetch QR code from the Node.js server
        server_url = "http://localhost:3000/connect-wallet"  # Ensure this endpoint is correct
        response = requests.get(server_url)

        if response.status_code == 200:
            qr_code_data = response.json().get("qrCode")
            if not qr_code_data:
                await message.reply("⚠️ QR code data is missing in the server response.")
                return

            # Decode the Base64-encoded QR code data
            qr_code_bytes = base64.b64decode(qr_code_data.split(",")[1])  # Skip the data:image/png;base64, part

            # Save QR code to a temporary file
            temp_file_path = "temp_qr.png"
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(qr_code_bytes)

            # Send the QR code as a photo using FSInputFile
            qr_code_file = FSInputFile(temp_file_path, filename="walletconnect_qr.png")
            await message.answer_photo(qr_code_file, caption="Scan this QR code to connect your wallet.")
        else:
            await message.reply(
                f"⚠️ Failed to fetch WalletConnect QR code. Server returned: {response.status_code}"
            )
    except Exception as e:
        await message.reply(f"⚠️ An error occurred: {str(e)}")
