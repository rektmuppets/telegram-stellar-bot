import asyncio
import sqlite3
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import socket
import json
import asyncpg
from stellar_sdk import Server
from globals import streaming_tasks, bot, dp  # No db_pool import
from trade import (TradeStates, arb_command, process_price, process_withdraw_amount, 
                  process_withdraw_address, withdraw_command, process_copy_trade, 
                  test_signal_command, add_trustline_command, add_copy_account, 
                  copy_trade_listener, copy_trade_menu_command, process_set_fixed_amount,
                  process_copy_trade_callback, process_set_multiplier, 
                  process_set_slippage, set_slippage_command, process_copy_wallet)
from utils import (init_db, load_keypair, list_copy_wallets, get_x_sentiment, 
                  fetch_copy_trades, parse_asset, async_stream_transactions, shutdown_flag,
                  copy_trading_stream, process_api_signal)

server = Server("https://horizon-testnet.stellar.org")

async def init_db_pool():
    try:
        db_pool = await asyncpg.create_pool(
            user='postgres',
            password='password',
            database='stellar_bot',
            host='127.0.0.1',
            port=5432
        )
        print("Database pool initialized successfully")
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    public_key TEXT NOT NULL,
                    encrypted_secret TEXT NOT NULL,
                    encryption_key TEXT NOT NULL
                )
            """)
            print("Users table ensured")
        return db_pool
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
    print("Received /start command")
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
        asset_issuer="GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
        amount="100",
        destination="GAW56XMB3ECEDW4MV7HHCPOCFUCZSONS7ZOYQLVYR7E4537E3D4YJNDN",
        db_pool=db_pool
    )

async def withdraw_address_wrapper(message: types.Message, state: FSMContext):
    global db_pool
    await process_withdraw_address(message, state, db_pool)

async def test_signal_wrapper(message: types.Message):
    global db_pool
    await test_signal_command(message, db_pool)

async def add_trustline_wrapper(message: types.Message):
    global db_pool
    await add_trustline_command(message, db_pool)

async def copy_trade_listener_wrapper(message: types.Message):
    global db_pool
    await copy_trade_listener(message, db_pool)

async def fetch_trades_wrapper(message: types.Message):
    global db_pool
    telegram_id = message.from_user.id
    print("Received /fetchtrades command")
    wallets = list_copy_wallets(telegram_id)
    print(f"Wallets from fetch_trades: {wallets}")
    if not wallets:
        await message.reply("No wallets to fetch trades from.")
        return
    wallet = wallets[0]
    trade = await fetch_copy_trades(wallet)
    if trade:
        await message.reply(f"Fetched trade: {trade}")
    else:
        await message.reply(f"No recent trades for {wallet}")

async def remove_copy_account(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("G"):
        await message.reply("Usage: /removecopy <stellar_address>")
        return
    wallet_address = args[1]
    telegram_id = message.from_user.id
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("DELETE FROM copy_trading WHERE user_id = ? AND wallet_address = ?", (telegram_id, wallet_address))
    if c.rowcount > 0:
        conn.commit()
        await message.reply(f"Removed copy trade account: {wallet_address}")
    else:
        await message.reply(f"Wallet {wallet_address} not found in your copy list.")
    conn.close()

async def start_streaming_command(message: types.Message):
    chat_id = message.chat.id
    telegram_id = message.from_user.id
    await message.reply("Starting trade streaming...")
    task = asyncio.create_task(copy_trading_stream(chat_id, telegram_id, dp, bot, db_pool))
    streaming_tasks[chat_id] = task

async def stop_streaming_command(message: types.Message):
    chat_id = message.chat.id
    if chat_id in streaming_tasks:
        streaming_tasks[chat_id].cancel()
        del streaming_tasks[chat_id]
        await message.reply("Stopped trade streaming.")
    else:
        await message.reply("No active streaming to stop.")

async def shutdown():
    print("Shutting down...")
    shutdown_flag.set()
    for task in streaming_tasks.values():
        task.cancel()
    await asyncio.gather(*streaming_tasks.values(), return_exceptions=True)
    await dp.stop_polling()
    await dp.storage.close()
    await bot.session.close()
    loop = asyncio.get_event_loop()
    for task in asyncio.all_tasks(loop):
        task.cancel()
    await asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)
    loop.stop()
    print("Shutdown complete.")

async def main():
    db_pool = await init_db_pool()
    
    # Define wrapper for process_copy_trade_callback
    async def copy_trade_callback_wrapper(callback: types.CallbackQuery, state: FSMContext):
        await process_copy_trade_callback(callback, state, db_pool)

    dp.message.register(register_command, Command("register"))
    dp.message.register(start_command, Command("start"))
    dp.message.register(cancel_command, Command("cancel"))
    dp.message.register(restart_command, Command("restart"))
    dp.message.register(sentiment_command, Command("sentiment"))
    dp.message.register(arb_command, Command("arb"))
    dp.callback_query.register(process_price, TradeStates.price)
    dp.message.register(withdraw_command, Command("withdraw"))
    dp.message.register(process_withdraw_amount, TradeStates.withdraw_amount)
    dp.message.register(lambda message, state: process_withdraw_address(message, state, db_pool), TradeStates.withdraw_address)
    dp.message.register(copy_trade_command, Command("copytrade"))
    dp.message.register(test_signal_wrapper, Command("testsignal"))
    dp.message.register(add_trustline_wrapper, Command("addtrust"))
    dp.message.register(add_copy_account, Command("addcopy"))
    dp.message.register(copy_trade_listener_wrapper, Command("copytrade_live"))
    dp.message.register(fetch_trades_wrapper, Command("fetchtrades"))
    dp.message.register(remove_copy_account, Command("removecopy"))
    dp.message.register(start_streaming_command, Command("startstreaming"))
    dp.message.register(stop_streaming_command, Command("stopstreaming"))
    dp.message.register(copy_trade_menu_command, Command("copytrade_menu"))
    dp.callback_query.register(copy_trade_callback_wrapper)  # Register wrapper without filters
    dp.message.register(process_set_multiplier, TradeStates.set_multiplier)
    dp.message.register(process_set_fixed_amount, TradeStates.set_fixed_amount)
    dp.message.register(set_slippage_command, Command("setslippage"))
    dp.message.register(process_set_slippage, TradeStates.set_slippage)
    dp.message.register(process_copy_wallet, TradeStates.copy_wallet)

    init_db()
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Starting polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Polling failed: {e}")
        await shutdown()
    finally:
        if 'db_pool' in locals():
            await db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())