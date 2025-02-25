import time
import sqlite3
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import load_keypair, list_copy_wallets, fetch_copy_trades
from stellar_sdk import Asset, Payment, ChangeTrust, TextMemo, PathPaymentStrictSend
from stellar_utils import build_transaction, server, TESTNET

class TradeStates(StatesGroup):
    price = State()
    amount = State()
    withdraw_amount = State()
    withdraw_address = State()

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
        
        tx = await build_transaction(account, keypair, operations)  # No memo for consistency
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

async def process_api_signal(message: types.Message, signal: dict, db_pool):
    telegram_id = message.from_user.id
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        print(f"Loaded account sequence: {account.sequence}")
        
        print(f"Signal received: {signal}")
        asset_code = signal["asset"]["code"]
        asset_issuer = signal["asset"]["issuer"]
        print(f"Asset code: {asset_code}, Issuer: {asset_issuer}")
        
        amount = signal["amount"]
        memo = signal.get("memo")
        action = signal.get("action")
        
        trade_asset = Asset(code=asset_code, issuer=asset_issuer)
        operations = []
        if action in ("trade", "trust_only"):
            operations.append(ChangeTrust(asset=trade_asset, limit="1000.0"))
        if action == "trade":
            send_amount = "101"
            paths = server.strict_send_paths(
                source_asset=Asset.native(),
                source_amount=send_amount,
                destination=[trade_asset]
            ).call()
            print(f"Available paths: {paths}")
            if not paths["_embedded"]["records"]:
                await message.reply("No SDEX path available for XLM -> USDC.")
                return
            
            operations.append(
                PathPaymentStrictSend(
                    send_asset=Asset.native(),
                    send_amount=send_amount,
                    destination=account.account.account_id,
                    dest_asset=trade_asset,
                    dest_min=amount,
                    path=[Asset.native(), trade_asset]
                )
            )
        
        if not operations:
            await message.reply(f"Unknown action: {action}")
            return
        
        tx = await build_transaction(account, keypair, operations, memo=memo)  # Pass memo to builder
        print(f"Transaction XDR before submit: {tx.to_xdr()}")
        
        response = server.submit_transaction(tx)
        print(f"Transaction submitted: {response}")
        await message.reply(f"Processed signal {signal['signal_id']}: {action} {amount} {asset_code} to self. Tx: {response['hash']}")
    except Exception as e:
        await message.reply(f"Signal processing failed: {str(e)}")

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
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO copy_trading (wallet_address) VALUES (?)", (wallet_address,))
        conn.commit()
        await message.reply(f"Added copy trade account: {wallet_address}")
    except sqlite3.IntegrityError:
        await message.reply("Account already added.")
    conn.close()

async def copy_trade_listener(message: types.Message, db_pool):
    wallets = list_copy_wallets()
    if not wallets:
        await message.reply("No copy trade accounts added.")
        return
    wallet = wallets[0]  # Use first account for now
    trade = await fetch_copy_trades(wallet)
    if not trade:
        await message.reply(f"No recent trades found for {wallet}.")
        return
    await process_api_signal(message, trade, db_pool)