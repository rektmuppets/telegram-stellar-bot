import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import os
import socket
import json
import asyncpg
from dotenv import load_dotenv

from trade import (TradeStates, arb_command, process_price, process_withdraw_amount, 
                  process_withdraw_address, withdraw_command, process_copy_trade, 
                  test_signal_command, add_trustline_command, add_copy_account, 
                  copy_trade_listener, process_api_signal, get_balance, has_trustline)
from utils import (init_db, load_keypair, list_copy_wallets, get_x_sentiment, 
                  fetch_copy_trades, parse_asset, async_stream_transactions, shutdown_flag)
from stellar_sdk import Server

streaming_tasks = {}

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN or not isinstance(TELEGRAM_TOKEN, str):
    raise ValueError("TELEGRAM_TOKEN not found in .env or invalid.")

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db_pool = None
server = Server("https://horizon-testnet.stellar.org")

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
    print("Received /fetchtrades command")
    wallets = list_copy_wallets()
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

async def set_copy_wallet_command(message: types.Message, state: FSMContext):
    await message.reply("Enter the Stellar address to copy trades from:")
    await state.set_state(TradeStates.copy_wallet)

async def process_copy_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text
    if not wallet_address.startswith("G"):
        await message.reply("Invalid Stellar address. Try again or /cancel.")
        return
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO copy_trading (wallet_address) VALUES (?)", (wallet_address,))
        conn.commit()
        await message.reply(f"Set to copy trades from: {wallet_address}")
    except sqlite3.IntegrityError:
        await message.reply("Wallet already added.")
    finally:
        conn.close()
    await state.clear()

async def remove_copy_account(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("G"):
        await message.reply("Usage: /removecopy <stellar_address>")
        return
    wallet_address = args[1]
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("DELETE FROM copy_trading WHERE wallet_address = ?", (wallet_address,))
    if c.rowcount > 0:
        conn.commit()
        await message.reply(f"Removed copy trade account: {wallet_address}")
    else:
        await message.reply(f"Wallet {wallet_address} not found in copy list.")
    conn.close()

async def copy_trading_stream(chat_id: int, telegram_id: int, dp: Dispatcher):
    print(f"Starting streaming task for chat_id: {chat_id}, telegram_id: {telegram_id}")
    while not shutdown_flag.is_set():
        try:
            wallets = list_copy_wallets()
            if not wallets:
                print("No wallets found to stream trades from.")
                await bot.send_message(chat_id, "No wallets to stream trades from.")
                await asyncio.sleep(60)
                continue
            wallet = wallets[-1]
            print(f"Streaming trades for {wallet}")
            stream_iter = await async_stream_transactions(wallet)
            async for tx in stream_iter:
                if shutdown_flag.is_set():
                    print("Shutdown flag set, exiting streaming loop.")
                    break
                print(f"New transaction: {tx['id']}")
                trade = await fetch_copy_trades(wallet)
                if trade and trade["signal_id"] == tx["id"]:
                    await process_api_signal_with_chat(chat_id, telegram_id, trade, dp)
                else:
                    print(f"No trade parsed or signal_id mismatch for tx: {tx['id']}")
        except Exception as e:
            print(f"Stream error: {e}, reconnecting in 5 seconds...")
            await asyncio.sleep(5)
    print("Streaming task ended.")

async def process_api_signal_with_chat(chat_id: int, telegram_id: int, signal: dict, dp: Dispatcher):
    try:
        print(f"Processing trade signal: {signal['signal_id']}")
        result = await process_api_signal(None, signal, db_pool, telegram_id, dp, chat_id=chat_id, bot=bot)  # Pass bot
        trade_info = (
            f"Copied trade {signal['signal_id']}:\n"
            f"Sent: {result['user_send_amount']} {result['send_asset_code']}\n"
            f"Received: {result['user_dest_min']} {result['dest_asset_code']}\n"
            f"Path: {', '.join([p['code'] for p in result['path']]) or 'Direct'}\n"
            f"Tx: {result['response']['hash']}"
        )
        await bot.send_message(chat_id, trade_info)
    except Exception as e:
        await bot.send_message(chat_id, f"Failed to copy trade {signal.get('signal_id', 'unknown')}: {str(e)}")

async def start_streaming_command(message: types.Message):
    chat_id = message.chat.id
    telegram_id = message.from_user.id
    await message.reply("Starting trade streaming...")
    print(f"Starting streaming command for chat_id: {chat_id}")
    task = asyncio.create_task(copy_trading_stream(chat_id, telegram_id, dp))
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

async def set_multiplier_command(message: types.Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /setmultiplier <value> (e.g., 0.5)")
        return
    try:
        multiplier = float(args[1])
        if 0 < multiplier <= 1:
            await state.update_data(multiplier=multiplier)
            data = await state.get_data()  # Verify state
            print(f"Set multiplier to {multiplier} for chat_id: {message.chat.id}, user_id: {message.from_user.id}, state: {data}")
            await message.reply(f"Multiplier set to {multiplier}")
        else:
            await message.reply("Multiplier must be between 0 and 1.")
    except ValueError:
        await message.reply("Invalid value. Use a number (e.g., 0.5).")

async def main():
    await init_db_pool()
    
    dp.message.register(register_command, Command("register"))
    dp.message.register(start_command, Command("start"))
    dp.message.register(cancel_command, Command("cancel"))
    dp.message.register(restart_command, Command("restart"))
    dp.message.register(sentiment_command, Command("sentiment"))
    dp.message.register(arb_command, Command("arb"))
    dp.callback_query.register(process_price, TradeStates.price)
    dp.message.register(withdraw_command, Command("withdraw"))
    dp.message.register(process_withdraw_amount, TradeStates.withdraw_amount)
    dp.message.register(withdraw_address_wrapper, TradeStates.withdraw_address)
    dp.message.register(copy_trade_command, Command("copytrade"))
    dp.message.register(test_signal_wrapper, Command("testsignal"))
    dp.message.register(add_trustline_wrapper, Command("addtrust"))
    dp.message.register(add_copy_account, Command("addcopy"))
    dp.message.register(copy_trade_listener_wrapper, Command("copytrade_live"))
    dp.message.register(fetch_trades_wrapper, Command("fetchtrades"))
    dp.message.register(set_copy_wallet_command, Command("setcopywallet"))
    dp.message.register(process_copy_wallet, TradeStates.copy_wallet)
    dp.message.register(remove_copy_account, Command("removecopy"))
    dp.message.register(start_streaming_command, Command("startstreaming"))
    dp.message.register(stop_streaming_command, Command("stopstreaming"))
    dp.message.register(set_multiplier_command, Command("setmultiplier"))

    init_db()
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Starting polling...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("Received KeyboardInterrupt, shutting down...")
        await shutdown()
        print("Bot stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}, shutting down...")
        await shutdown()
    finally:
        await dp.storage.close()
        await bot.session.close()
        print("Final cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())        