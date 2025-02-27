import time
import sqlite3
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import load_keypair, list_copy_wallets, fetch_copy_trades
from stellar_sdk import Asset, Payment, ChangeTrust, TextMemo, PathPaymentStrictSend, PathPaymentStrictReceive
from stellar_utils import build_transaction, server, TESTNET

class TradeStates(StatesGroup):
    price = State()
    amount = State()
    withdraw_amount = State()
    withdraw_address = State()
    copy_wallet = State()

def get_balance(account, asset):
    """Get the balance of an asset for an account."""
    for balance in account.raw_data["balances"]:
        if asset.is_native() and balance["asset_type"] == "native":
            return balance["balance"]
        elif (balance["asset_type"] != "native" and
              balance["asset_code"] == asset.code and
              balance["asset_issuer"] == asset.issuer):
            return balance["balance"]
    return "0"

def has_trustline(account, asset):
    for balance in account.raw_data["balances"]:
        if asset.is_native() and balance["asset_type"] == "native":
            return True
        elif (balance["asset_type"] != "native" and
              balance["asset_code"] == asset.code and
              balance["asset_issuer"] == asset.issuer):
            return True
    return False

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

# trade.py
async def process_api_signal(message: types.Message | None, signal: dict, db_pool, telegram_id: int = None, dp=None):
    telegram_id = message.from_user.id if message else telegram_id
    if not telegram_id:
        raise ValueError("No valid telegram_id provided for streaming")
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)

        # Replace multiplier definition with FSM logic
        multiplier = 0.1  # Default
        if dp:
            state = FSMContext(storage=dp.storage, key=telegram_id)
            data = await state.get_data()
            multiplier = data.get("multiplier", 0.1)

        operation_type = signal["operation_type"]
        send_asset_dict = signal["send_asset"]
        dest_asset_dict = signal["dest_asset"]
        path = signal["path"]
        orig_send_amount = float(signal["send_amount"])
        orig_dest_amount = float(signal["dest_amount"])

        send_asset = (Asset.native() if send_asset_dict["code"] == "XLM"
                      else Asset(send_asset_dict["code"], send_asset_dict["issuer"]))
        dest_asset = (Asset.native() if dest_asset_dict["code"] == "XLM"
                      else Asset(dest_asset_dict["code"], dest_asset_dict["issuer"]))
        path_assets = [Asset.native() if p["code"] == "XLM"
                       else Asset(p["code"], p["issuer"]) for p in path]

        operations = []
        for asset in [send_asset, dest_asset] + path_assets:
            if not asset.is_native():
                print(f"Checking trustline for {asset.code} ({asset.issuer})")
                if not has_trustline(account, asset):
                    print(f"Adding trustline for {asset.code}")
                    operations.append(ChangeTrust(asset=asset, limit=None))

        slippage = 0.01
        effective_rate = orig_dest_amount / orig_send_amount

        user_send_amount = None
        user_dest_min = None
        if operation_type == "path_payment_strict_send":
            user_send_amount = str(orig_send_amount * multiplier)
            user_dest_min = "{:.7f}".format(float(user_send_amount) * effective_rate * (1 - slippage))
            send_balance = float(get_balance(account, send_asset))
            if send_balance < float(user_send_amount):
                error_msg = f"Insufficient {send_asset.code} balance: {send_balance} < {user_send_amount}"
                if message:
                    await message.reply(error_msg)
                else:
                    print(error_msg)
                return
            operations.append(
                PathPaymentStrictSend(
                    send_asset=send_asset,
                    send_amount=user_send_amount,
                    destination=keypair.public_key,
                    dest_asset=dest_asset,
                    dest_min=user_dest_min,
                    path=path_assets
                )
            )
        elif operation_type == "path_payment_strict_receive":
            user_dest_amount = str(orig_dest_amount * multiplier)
            user_send_max = "{:.7f}".format(float(user_dest_amount) / effective_rate * (1 + slippage))
            send_balance = float(get_balance(account, send_asset))
            if send_balance < float(user_send_max):
                await message.reply(f"Warning: {send_asset.code} balance {send_balance} < calculated send_max {user_send_max}")
            operations.append(
                PathPaymentStrictReceive(
                    send_asset=send_asset,
                    send_max=user_send_max,
                    destination=keypair.public_key,
                    dest_asset=dest_asset,
                    dest_amount=user_dest_amount,
                    path=path_assets
                )
            )
        else:
            await message.reply(f"Unsupported operation type: {operation_type}")
            return

        tx = await build_transaction(account, keypair, operations)
        print(f"Transaction XDR before submit: {tx.to_xdr()}")
        response = server.submit_transaction(tx)
        success_msg = (f"Copied {operation_type}: {user_send_amount if operation_type == 'path_payment_strict_send' else user_send_max} "
                       f"{send_asset.code} → {user_dest_amount if operation_type == 'path_payment_strict_receive' else user_dest_min} "
                       f"{dest_asset.code}. Tx: {response['hash']}")
        if message:
            await message.reply(success_msg)
        else:
            print(success_msg)
        return {
            "response": response,
            "user_send_amount": user_send_amount,
            "user_dest_min": user_dest_min,
            "send_asset_code": send_asset.code,
            "dest_asset_code": dest_asset.code,
            "path": signal["path"]
        }
    except Exception as e:
        error_msg = f"Copy trade failed: {str(e)}"
        if message:
            await message.reply(error_msg)
        else:
            print(error_msg)
        raise

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
    wallet = wallets[-1]
    trade = await fetch_copy_trades(wallet)
    if not trade:
        await message.reply(f"No recent trades found for {wallet} or parsing failed. Check logs.")
        return
    await process_api_signal(message, trade, db_pool)