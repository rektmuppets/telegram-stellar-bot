import time
import sqlite3
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import asyncio
from utils import load_keypair, list_copy_wallets, fetch_copy_trades, process_api_signal, copy_trading_stream
from stellar_sdk import Asset, Payment, ChangeTrust, TextMemo, PathPaymentStrictSend, PathPaymentStrictReceive
from stellar_utils import build_transaction, server, TESTNET
from globals import streaming_tasks, dp, bot  # No db_pool

class TradeStates(StatesGroup):
    price = State()
    amount = State()
    withdraw_amount = State()
    withdraw_address = State()
    copy_wallet = State()
    set_multiplier = State()
    set_fixed_amount = State()
    set_slippage = State()

async def arb_command(message: types.Message, state: FSMContext):
    prices = [0.05, 0.1, 0.25, 0.5]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{price} XLM/USDC", callback_data=f"price_{price}") for price in prices],
        [InlineKeyboardButton(text="Cancel", callback_data="cancel")]
    ])
    await message.reply("Select a price for USDC arbitrage:", reply_markup=keyboard)
    await state.set_state(TradeStates.price)

async def process_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("Cancelled.")
        return
    price = float(callback.data.split("_")[1])
    await state.update_data(price=price)
    await callback.message.edit_text(f"Selected price: {price}. Enter amount:")
    await state.set_state(TradeStates.amount)

async def withdraw_command(message: types.Message, state: FSMContext):
    await message.reply("Enter amount to withdraw (XLM):")
    await state.set_state(TradeStates.withdraw_amount)

async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await message.reply("Enter destination address:")
        await state.set_state(TradeStates.withdraw_address)
    except ValueError:
        await message.reply("Invalid amount. Try again or /cancel.")

async def process_withdraw_address(message: types.Message, state: FSMContext, db_pool):
    address = message.text
    data = await state.get_data()
    amount = data["amount"]
    telegram_id = message.from_user.id
    try:
        if db_pool is None:
            await message.reply("Database pool is not initialized")
            await state.clear()
            return
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        
        operations = [
            Payment(
                destination=address,
                asset=Asset.native(),
                amount=str(amount)
            )
        ]
        
        tx = await build_transaction(account, keypair, operations)
        response = server.submit_transaction(tx)
        await message.reply(f"Withdrawn {amount} XLM to {address}. Tx: {response['hash']}")
        await state.clear()
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
        await state.clear()

async def process_copy_trade(message: types.Message, asset_code: str, asset_issuer: str, amount: str, destination: str, db_pool):
    telegram_id = message.from_user.id
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        
        new_asset = Asset(code=asset_code, issuer=asset_issuer)
        operations = [
            ChangeTrust(asset=new_asset, limit="1000.0"),
            PathPaymentStrictSend(
                send_asset=Asset.native(),
                send_amount="101",
                destination=account.account.account_id,
                dest_asset=new_asset,
                dest_min=amount,
                path=[Asset.native(), new_asset]
            )
        ]
        
        tx = await build_transaction(account, keypair, operations)
        response = server.submit_transaction(tx)
        await message.reply(f"Copied trade: Trusted {asset_code} and swapped {amount} {asset_code} to self. Tx: {response['hash']}")
    except Exception as e:
        await message.reply(f"Copy trade failed: {str(e)}")

async def add_trustline_command(message: types.Message, db_pool):
    telegram_id = message.from_user.id
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        
        usdc_asset = Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")
        operations = [ChangeTrust(asset=usdc_asset, limit="1000.0")]
        
        tx = await build_transaction(account, keypair, operations)
        response = server.submit_transaction(tx)
        await message.reply(f"Trustline added for USDC. Tx: {response['hash']}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

async def test_signal_command(message: types.Message, db_pool):
    mock_signal = {
        "signal_id": "12345",
        "action": "trade",
        "asset": {
            "code": "USDC",
            "issuer": "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
        },
        "amount": "100.50",
        "destination": "GDX2MUF37CFLY7QWBTBKIZZSRYGQOAWQYSG4ACKN7X5FV7HSATXCNGBY",  # Self for consistency
        "memo": "CopyTrade12345",
        "timestamp": "2025-02-22T10:00:00Z"
    }
    await process_api_signal(message, mock_signal, db_pool)

async def add_copy_account(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("G"):
        await message.reply("Usage: /addcopy <stellar_address>")
        return
    wallet_address = args[1]
    telegram_id = message.from_user.id
    
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM copy_trading WHERE user_id = ?", (telegram_id,))
    count = c.fetchone()[0]
    if count >= 20:
        await message.reply("You’ve reached the maximum of 20 copy trade addresses.")
        conn.close()
        return
    
    try:
        c.execute("INSERT INTO copy_trading (user_id, wallet_address) VALUES (?, ?)", (telegram_id, wallet_address))
        conn.commit()
        await message.reply(f"Added copy trade account: {wallet_address}")
    except sqlite3.IntegrityError:
        await message.reply("This address is already being copied by you.")
    conn.close()

async def copy_trade_listener(message: types.Message, db_pool):
    telegram_id = message.from_user.id
    wallets = list_copy_wallets(telegram_id)
    if not wallets:
        await message.reply("No copy trade accounts added.")
        return
    wallet = wallets[-1]  # Example: use the most recent wallet
    trade = await fetch_copy_trades(wallet)
    if not trade:
        await message.reply(f"No recent trades found for {wallet} or parsing failed. Check logs.")
        return
    await process_api_signal(message, trade, db_pool)
    
async def copy_trade_menu_command(message: types.Message, status_update: str = None):
    telegram_id = message.from_user.id
    chat_id = message.chat.id
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT id, wallet_address, status FROM copy_trading WHERE user_id = ?", (telegram_id,))
    addresses = c.fetchall()
    conn.close()
    
    streaming_active = chat_id in streaming_tasks and not streaming_tasks[chat_id].done()
    response = f"Copy Trade Addresses{' (Streaming)' if streaming_active else ''}:\n\n"
    if status_update:
        response += f"{status_update}\n\n"
    if not addresses:
        response += "No copy trade addresses added.\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Address", callback_data="add_copy")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, (addr_id, addr, status) in enumerate(addresses, 1):
            status_dot = "🟢" if status == "active" else "🟠"
            addr_short = f"{addr[:7]}...{addr[-7:]}"
            response += f"{status_dot} Copy {i} — {addr_short}\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"{status_dot} {i}-", callback_data=f"wallet_{addr_id}")
            ])
        global_status = "🟢" if streaming_active else "🟠"
        global_action = "Stop All" if streaming_active else "Copy Trade Global"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"{global_status} {global_action}", callback_data="toggle_global_stream")
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="➕ Add Address", callback_data="add_copy")
        ])
    
    if message.text == "/copytrade_menu":
        await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
    else:
        try:
            await message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        except TelegramBadRequest:
            await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)

async def wallet_settings_menu(callback: types.CallbackQuery, addr_id: int, telegram_id: int):
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT wallet_address, status, multiplier, fixed_amount FROM copy_trading WHERE id = ? AND user_id = ?", (addr_id, telegram_id))
    result = c.fetchone()
    conn.close()
    
    if not result:
        await callback.message.edit_text("Address not found.")
        return
    
    addr, status, mult, fixed = result
    status_dot = "🟢" if status == "active" else "🟠"
    addr_short = f"{addr[:7]}...{addr[-7:]}"
    buy_amount = f"Fixed: {fixed} XLM" if fixed else f"Percentage: {mult * 100}%"
    
    response = f"Settings for {addr_short} ({status_dot}):\n\n"
    response += f"Target Wallet: {addr_short}\n"
    response += f"Buy Amount: {buy_amount}\n"
    # Slippage is global in user_settings for now
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT slippage FROM user_settings WHERE user_id = ?", (telegram_id,))
    slippage_result = c.fetchone()
    slippage = slippage_result[0] * 100 if slippage_result and slippage_result[0] is not None else 5.0
    conn.close()
    response += f"Slippage: {slippage}%\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Toggle Pause" if status == "active" else "Toggle Resume", callback_data=f"{'pause' if status == 'active' else 'resume'}_{addr_id}")],
        [InlineKeyboardButton(text="Set Buy Amount", callback_data=f"setbuy_{addr_id}")],
        [InlineKeyboardButton(text="Delete", callback_data=f"delete_{addr_id}")],
        [InlineKeyboardButton(text="Back", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(response, reply_markup=keyboard)

async def process_copy_trade_callback(callback: types.CallbackQuery, state: FSMContext, db_pool):
    print(f"Callback received: {callback.data}")
    action = callback.data
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id
    print(f"Action: {action}, Chat ID: {chat_id}")
    
    if action.startswith("wallet_"):
        addr_id = int(action.split("_")[1])
        await wallet_settings_menu(callback, addr_id, telegram_id)
    
    elif action.startswith("pause_") or action.startswith("resume_"):
        conn = sqlite3.connect("copy_trading.db")
        c = conn.cursor()
        new_status = "paused" if action.startswith("pause") else "active"
        addr_id = int(action.split("_")[1])
        c.execute("UPDATE copy_trading SET status = ? WHERE id = ? AND user_id = ?", (new_status, addr_id, telegram_id))
        conn.commit()
        conn.close()
        await wallet_settings_menu(callback, addr_id, telegram_id)
    
    elif action.startswith("setbuy_"):
        await state.set_state(TradeStates.set_multiplier)
        addr_id = int(action.split("_")[1])
        await state.update_data(addr_id=addr_id)
        await callback.message.edit_text("Enter buy amount (e.g., '0.1' for 0.1 XLM fixed, or '50%' for 50% of target):")
    
    elif action.startswith("delete_"):
        conn = sqlite3.connect("copy_trading.db")
        c = conn.cursor()
        addr_id = int(action.split("_")[1])
        c.execute("DELETE FROM copy_trading WHERE id = ? AND user_id = ?", (addr_id, telegram_id))
        conn.commit()
        conn.close()
        await copy_trade_menu_command(callback.message, status_update="Deleted address.")
    
    elif action == "back_to_menu":
        await copy_trade_menu_command(callback.message)
    
    elif action == "toggle_global_stream":
        print(f"Toggle global stream triggered for chat_id: {chat_id}")
        if chat_id in streaming_tasks and not streaming_tasks[chat_id].done():
            streaming_tasks[chat_id].cancel()
            try:
                await streaming_tasks[chat_id]
            except asyncio.CancelledError:
                print(f"Streaming task cancelled for chat_id: {chat_id}")
            del streaming_tasks[chat_id]
            await copy_trade_menu_command(callback.message, status_update="Global streaming stopped.")
        else:
            task = asyncio.create_task(copy_trading_stream(chat_id, telegram_id, dp, bot, db_pool))
            streaming_tasks[chat_id] = task
            print(f"Started streaming task: {task}")
            status_update = "Global streaming started."
            await copy_trade_menu_command(callback.message, status_update="Global streaming started.")    
    
    elif action == "add_copy":
        await callback.message.reply("Enter the Stellar address to copy (e.g., GABC...):")  # Changed to reply
        await state.set_state(TradeStates.copy_wallet)
    
    await callback.answer()

async def process_set_multiplier(message: types.Message, state: FSMContext):
    try:
        input_val = message.text.strip()
        telegram_id = message.from_user.id
        data = await state.get_data()
        addr_id = data["addr_id"]
        
        if input_val.endswith("%"):
            multiplier = float(input_val[:-1]) / 100
            if not 0 < multiplier <= 1:
                await message.reply("Percentage must be between 0 and 100%. Try again.")
                return
            fixed_amount = None
        else:
            fixed_amount = float(input_val)
            if fixed_amount <= 0:
                await message.reply("Fixed amount must be positive. Try again.")
                return
            multiplier = 1.0
        
        conn = sqlite3.connect("copy_trading.db")
        c = conn.cursor()
        c.execute("UPDATE copy_trading SET multiplier = ?, fixed_amount = ? WHERE id = ? AND user_id = ?", 
                  (multiplier, fixed_amount, int(addr_id), telegram_id))
        conn.commit()
        conn.close()
        
        await message.reply(f"Buy amount set to {input_val}")
        await copy_trade_menu_command(message)
        await state.clear()
    except ValueError:
        await message.reply("Invalid input. Use '0.1' for fixed XLM or '50%' for percentage.")

async def process_set_fixed_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.reply("Amount must be positive. Try again.")
            return
        data = await state.get_data()
        address = data["address"]
        telegram_id = message.from_user.id
        conn = sqlite3.connect("copy_trading.db")
        c = conn.cursor()
        c.execute("UPDATE copy_trading SET fixed_amount = ?, multiplier = 1.0 WHERE user_id = ? AND wallet_address = ?", (amount, telegram_id, address))
        conn.commit()
        conn.close()
        await message.reply(f"Fixed amount set to {amount} XLM for {address[:6]}...{address[-6:]}")
        await copy_trade_menu_command(message)
        await state.clear()
    except ValueError:
        await message.reply("Invalid number. Try again.")

async def set_slippage_command(message: types.Message, state: FSMContext):
    await message.reply("Enter slippage percentage (0-10%, e.g., 5 for 5%):")
    await state.set_state(TradeStates.set_slippage)

async def process_set_slippage(message: types.Message, state: FSMContext):
    try:
        slippage_pct = float(message.text)
        if not 0 <= slippage_pct <= 10:
            await message.reply("Slippage must be between 0 and 10%. Try again.")
            return
        slippage = slippage_pct / 100
        telegram_id = message.from_user.id
        conn = sqlite3.connect("copy_trading.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_settings (user_id, slippage) VALUES (?, ?)", (telegram_id, slippage))
        conn.commit()
        conn.close()
        await message.reply(f"Slippage set to {slippage_pct}%")
        await state.clear()
    except ValueError:
        await message.reply("Invalid number. Try again.")

async def process_copy_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text.strip()
    if not wallet_address.startswith("G") or len(wallet_address) < 56:
        await message.reply("Invalid Stellar address. Use /copytrade_menu to try again.")
        await state.clear()
        return
    
    telegram_id = message.from_user.id
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM copy_trading WHERE user_id = ?", (telegram_id,))
    count = c.fetchone()[0]
    if count >= 20:
        await message.reply("You’ve reached the maximum of 20 copy trade addresses.")
        conn.close()
        await state.clear()
        return
    
    try:
        c.execute("INSERT INTO copy_trading (user_id, wallet_address) VALUES (?, ?)", (telegram_id, wallet_address))
        conn.commit()
        await message.reply(f"Added copy trade account: {wallet_address}")
    except sqlite3.IntegrityError:
        await message.reply("This address is already being copied by you.")
    conn.close()
    await copy_trade_menu_command(message, status_update=f"Added {wallet_address[:7]}...{wallet_address[-7:]}")
    await state.clear()