import time
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import load_keypair
from stellar_sdk import Asset, Payment, ChangeTrust
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
            ChangeTrust(
                asset=new_asset,
                limit="1000.0"
            ),
            Payment(
                destination=destination,
                asset=new_asset,
                amount=amount
            )
        ]
        
        tx = await build_transaction(account, keypair, operations)
        response = server.submit_transaction(tx)
        await message.reply(f"Copied trade: Trusted {asset_code} and sent {amount} to {destination}. Tx: {response['hash']}")
    except Exception as e:
        await message.reply(f"Copy trade failed: {str(e)}")

async def add_trustline_command(message: types.Message, db_pool):
    telegram_id = message.from_user.id
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        
        usdc_asset = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5GMCOP5PXD")
        operations = [
            ChangeTrust(
                asset=usdc_asset,
                limit="1000.0"
            )
        ]
        
        tx = await build_transaction(account, keypair, operations)
        response = server.submit_transaction(tx)
        await message.reply(f"Trustline added for USDC. Tx: {response['hash']}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")