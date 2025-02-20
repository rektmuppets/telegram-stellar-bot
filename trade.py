from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from utils import load_keypair
import logging

horizon = Server("https://horizon-testnet.stellar.org")
bot_kp = load_keypair()
logger = logging.getLogger(__name__)

async def start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Trade", callback_data="trade")],
        [InlineKeyboardButton(text="Withdraw", callback_data="withdraw")]
    ])
    await message.reply(f"Fund me (Testnet): {bot_kp.public_key}", reply_markup=kb)
    logger.info(f"Started bot for user {message.from_user.id}")

async def trade_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Arb USDC", callback_data="arb_usdc")]
    ])
    await callback.message.edit_text("Choose trade:", reply_markup=kb)
    logger.info(f"User {callback.from_user.id} opened trade menu")

async def arb_usdc(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Enter amount (e.g., 5):")
    await state.set_state("arb_amount")
    logger.info(f"User {callback.from_user.id} prompted for arb amount, state set to arb_amount")

async def arb_amount(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"User {message.from_user.id} in state {current_state}, input: {message.text}")
    amount = message.text.strip()
    try:
        float(amount)
        acct = horizon.load_account(bot_kp.public_key)
        tx_builder = TransactionBuilder(
            source_account=acct,
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            base_fee=100
        )
        tx_builder = tx_builder.add_time_bounds(0, 0)
        tx_builder = tx_builder.append_manage_buy_offer_op(
            selling=Asset.native(),
            buying=Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"),
            amount=amount,
            price="0.10"
        )
        tx = tx_builder.build()
        tx.sign(bot_kp)
        horizon.submit_transaction(tx)
        await message.reply(f"Arbed {amount} USDC on Testnet!")
        await state.clear()
        logger.info(f"User {message.from_user.id} arbed {amount} USDC successfully")
    except ValueError:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Start", callback_data="restart")]
        ])
        await message.reply("Invalid amount! Please enter a number (e.g., 5).", reply_markup=kb)
        logger.warning(f"User {message.from_user.id} entered invalid arb amount: {amount}")
    except Exception as e:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Start", callback_data="restart")]
        ])
        await message.reply(f"Error: {str(e)}\nTry again or go back:", reply_markup=kb)
        logger.error(f"User {message.from_user.id} hit arb error: {str(e)}")

async def withdraw_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Enter amount and address (e.g., 5 GAW56...):")
    await state.set_state("withdraw_process")
    logger.info(f"User {callback.from_user.id} prompted for withdraw input, state set to withdraw_process")

async def withdraw_process(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"User {message.from_user.id} in state {current_state}, input: {message.text}")
    args = message.text.strip().split()
    if len(args) != 2:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Start", callback_data="restart")]
        ])
        await message.reply("Invalid input! Use: <amount> <address> (e.g., 5 GAW56...).", reply_markup=kb)
        logger.warning(f"User {message.from_user.id} entered invalid withdraw input: {message.text}")
        return
    amount, dest = args[0], args[1]
    try:
        float(amount)
        if not dest.startswith("G") or len(dest) != 56:
            raise ValueError("Invalid Stellar address")
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
        await state.clear()
        logger.info(f"User {message.from_user.id} withdrew {amount} XLM to {dest} successfully")
    except ValueError as e:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Start", callback_data="restart")]
        ])
        await message.reply(f"Invalid input: {str(e)}! Use: <amount> <address> (e.g., 5 GAW56...).", reply_markup=kb)
        logger.warning(f"User {message.from_user.id} hit withdraw ValueError: {str(e)}")
    except Exception as e:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Start", callback_data="restart")]
        ])
        await message.reply(f"Error: {str(e)}\nTry again or go back:", reply_markup=kb)
        logger.error(f"User {message.from_user.id} hit withdraw error: {str(e)}")