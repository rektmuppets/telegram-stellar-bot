import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Init
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
horizon = Server("https://horizon-testnet.stellar.org")
with open("bot_key.enc", "rb") as f:
    encrypted_secret = f.read()
cipher = Fernet(os.getenv("ENCRYPTION_KEY"))
secret = cipher.decrypt(encrypted_secret).decode()
bot_kp = Keypair.from_secret(secret)

# Commands
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply(f"Fund me (Testnet): {bot_kp.public_key}")

@dp.message(Command("arb"))
async def arbitrage(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply("Usage: /arb <asset> <amount>")
        return
    asset_code, amount = args[1], args[2]
    try:
        acct = horizon.load_account(bot_kp.public_key)
        tx_builder = TransactionBuilder(
            source_account=acct,
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )
        tx_builder = tx_builder.add_time_bounds(0, 0)
        tx_builder = tx_builder.append_manage_buy_offer_op(
            selling=Asset.native(),  # Sell XLM
            buying=Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"),  # Buy USDC
            amount=amount,  # Amount of USDC to buy
            price="0.10"  # XLM per USDC
        )
        tx = tx_builder.build()
        tx.sign(bot_kp)
        horizon.submit_transaction(tx)
        await message.reply(f"Arbed {amount} USDC on Testnet!")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

@dp.message(Command("withdraw"))
async def withdraw(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply("Usage: /withdraw <amount> <address>")
        return
    amount, dest = args[1], args[2]
    try:
        acct = horizon.load_account(bot_kp.public_key)
        tx_builder = TransactionBuilder(
            source_account=acct,
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )
        tx_builder = tx_builder.add_time_bounds(0, 0)
        tx_builder = tx_builder.append_payment_op(
            destination=dest,
            asset=Asset.native(),
            amount=amount
        )
        tx = tx_builder.build()
        tx.sign(bot_kp)
        horizon.submit_transaction(tx)
        await message.reply(f"Withdrew {amount} XLM to {dest}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

# Run
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())