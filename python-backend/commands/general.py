from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

# Create a router for general commands
router = Router()

# Handlers
@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Hello! I'm your Stellar bot.\nUse /help to see available commands.")

@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/balance - Check your Stellar account balance\n"
        "/register - Register your wallet and generate a lightweight signer passkey\n"
        "/connectwallet - Connect your wallet via WalletConnect\n"
        "/testsign - Test a transaction with your lightweight signer\n"
        "/removesigner - Remove the lightweight signer from your wallet\n"
    )

# Register commands
def register_general_commands(dp):
    dp.include_router(router)
