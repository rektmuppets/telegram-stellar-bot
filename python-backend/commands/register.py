import logging
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from stellar_sdk import Keypair, TransactionBuilder, Network, Server
from io import BytesIO
import qrcode
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
HORIZON_URL = os.getenv("HORIZON_URL", "https://horizon-testnet.stellar.org")

# Initialize Stellar server
server = Server(HORIZON_URL)

# In-memory storage for user data
user_keys = {}

async def register_command(message: Message):
    """
    Handles the /register command to add the bot as a lightweight signer.
    Provides a fallback for wallets without WalletConnect support.
    """
    try:
        user_id = message.from_user.id
        user_data = user_keys.get(user_id)

        if not user_data or not user_data.get("verified"):
            await message.answer("Please verify your account ownership first using /verify.")
            return

        # Load user public key and generate bot keypair
        user_public_key = user_data["public_key"]
        bot_keypair = Keypair.random()  # Generate a new bot keypair
        bot_private_key = bot_keypair.secret  # Securely store this in your database
        bot_public_key = bot_keypair.public_key

        # Save bot keypair securely
        user_keys[user_id]["bot_private_key"] = bot_private_key

        # Load user account from Horizon
        account = server.load_account(user_public_key)

        # Create a transaction to add the bot as a signer
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_set_options_op(
                signer_type="ed25519_public_key",
                signer_key=bot_public_key,
                signer_weight=1,  # Lightweight signer
            )
            .append_set_options_op(
                low_threshold=1,
                med_threshold=2,
                high_threshold=3,
            )
            .set_timeout(30)
            .build()
        )

        # Generate QR code for the transaction
        qr_data = transaction.to_xdr()
        qr = qrcode.QRCode(box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img_buffer = BytesIO()
        qr_img = qr.make_image(fill="black", back_color="white")
        qr_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        # Send QR code to user
        input_file = FSInputFile(img_buffer, filename="register_qr.png")
        await message.answer_photo(
            photo=input_file,
            caption="Scan this QR code with your wallet to register the bot as a signer."
        )
    except Exception as e:
        logging.error(f"Error in /register: {e}")
        await message.answer("An error occurred during registration. Please try again.")

# Register the /register command
def register_register_commands(dp):
    dp.message.register(register_command, Command("register"))
