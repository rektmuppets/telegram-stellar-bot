import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import os
import socket
import json
import asyncpg
from dotenv import load_dotenv

from trade import TradeStates, arb_command, process_price, process_withdraw_amount, process_withdraw_address, withdraw_command, process_copy_trade
from utils import init_db, load_keypair, list_copy_wallets, get_x_sentiment

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN or not isinstance(TELEGRAM_TOKEN, str):
    raise ValueError("TELEGRAM_TOKEN not found in .env or invalid. Please set it as TELEGRAM_TOKEN=your_token_here")

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
db_pool = None

async def init_db_pool():
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            user='postgres',
            password='password',
            database='stellar_bot',
            host='localhost',
            port=5432
        )
        print("Database pool initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database pool: {e}")
        raise

async def request_keypair(telegram_id):
    loop = asyncio.get_event_loop()
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connecting to localhost:5000 for telegram_id: {telegram_id}")
    client.connect(('localhost', 5000))
    request = {"telegram_id": str(telegram_id)}
    print(f"Sending request: {request}")
    client.send(json.dumps(request).encode())
    response_data = await loop.run_in_executor(None, client.recv, 4096)
    if not response_data:
        raise ValueError("No response from mock enclave server")
    response = json.loads(response_data.decode())
    print(f"Received response: {response}")
    client.close()
    return response

async def register_command(message: types.Message):
    global db_pool
    telegram_id = message.from_user.id
    async with db_pool.acquire() as conn:
        exists = await conn.fetchval("SELECT telegram_id FROM users WHERE telegram_id = $1", telegram_id)
        if exists:
            await message.reply("You’re already registered!")
            return
    
    try:
        response = await request_keypair(telegram_id)
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (telegram_id, public_key, encrypted_secret, encryption_key)
                VALUES ($1, $2, $3, $4)
            """, telegram_id, response["public_key"], response["encrypted_secret"], response["encryption_key"])
        await message.reply(f"Registered! Your public key: {response['public_key']}")
    except Exception as e:
        await message.reply(f"Registration failed: {str(e)}")

async def start_command(message: types.Message):
    await message.reply("Welcome to @photonbot! Use /arb, /withdraw, /sentiment, or /copy features.")

async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Action cancelled. Use /start to begin again.")

async def restart_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Bot restarted. Use /start to begin.")

async def sentiment_command(message: types.Message):
    score = await get_x_sentiment("USDC/XLM")
    await message.reply(f"USDC/XLM Sentiment: {score:.2f} (-1 bearish, +1 bullish)")

async def copy_trade_command(message: types.Message):
    global db_pool
    await process_copy_trade(
        message,
        asset_code="USDC",
        asset_issuer="GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5GMCOP5PXD",
        amount="100",
        destination="GAW56XMB3ECEDW4MV7HHCPOCFUCZSONS7ZOYQLVYR7E4537E3D4YJNDN",
        db_pool=db_pool
    )

async def withdraw_address_wrapper(message: types.Message, state: FSMContext):  # New wrapper function
    global db_pool
    await process_withdraw_address(message, state, db_pool)

async def copy_trading_loop():
    while True:
        try:
            wallets = list_copy_wallets()
            for wallet in wallets:
                print(f"Checking offers for {wallet}")
        except Exception as e:
            print(f"Error in copy_trading_loop: {e}")
        await asyncio.sleep(300)

async def main():
    await init_db_pool()
    
    dp = Dispatcher(storage=storage)
    
    dp.message.register(register_command, Command("register"))
    dp.message.register(start_command, Command("start"))
    dp.message.register(cancel_command, Command("cancel"))
    dp.message.register(restart_command, Command("restart"))
    dp.message.register(sentiment_command, Command("sentiment"))
    dp.message.register(arb_command, Command("arb"))
    dp.callback_query.register(process_price, TradeStates.price)
    dp.message.register(withdraw_command, Command("withdraw"))
    dp.message.register(process_withdraw_amount, TradeStates.withdraw_amount)
    dp.message.register(withdraw_address_wrapper, TradeStates.withdraw_address)  # Use wrapper
    dp.message.register(copy_trade_command, Command("copytrade"))

    init_db()
    asyncio.create_task(copy_trading_loop())
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())