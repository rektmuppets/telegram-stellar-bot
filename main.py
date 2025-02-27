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
                  fetch_copy_trades, parse_asset, async_stream_transactions)
from stellar_sdk import Server

streaming_tasks = {}
shutdown_flag = asyncio.Event()

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

async def start_command(message: types.Message):
    print("Received /start command")
    await message.reply("Welcome to @photonbot! Use /arb, /withdraw, /sentiment, or /copy features.")

async def copy_trading_stream(chat_id: int, telegram_id: int, dp: Dispatcher):
    print(f"Starting streaming task for chat_id: {chat_id}, telegram_id: {telegram_id}")
    while not shutdown_flag.is_set():
        try:
            wallets = list_copy_wallets()
            print(f"Wallets: {wallets}")
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
        result = await process_api_signal(None, signal, db_pool, telegram_id, dp)
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

async def shutdown():
    print("Shutting down...")
    shutdown_flag.set()
    for task in streaming_tasks.values():
        task.cancel()
    await asyncio.gather(*streaming_tasks.values(), return_exceptions=True)
    await dp.stop_polling()
    await dp.storage.close()
    await bot.session.close()

async def main():
    await init_db_pool()
    
    dp.message.register(start_command, Command("start"))
    dp.message.register(start_streaming_command, Command("startstreaming"))
    dp.message.register(stop_streaming_command, Command("stopstreaming"))
    dp.message.register(fetch_trades_wrapper, Command("fetchtrades"))

    init_db()
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Starting polling...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        await shutdown()
        print("Bot stopped by user.")
    finally:
        await dp.storage.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())