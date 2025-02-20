import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os
from trade import start as trade_start, trade_menu, arb_usdc, arb_amount, withdraw_menu, withdraw_process, copy_setup
from utils import load_keypair

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot_kp = load_keypair()

class TradeStates(StatesGroup):
    arb_amount = State()
    withdraw_process = State()

dp.message(Command("start"))(trade_start)
dp.callback_query(lambda c: c.data == "trade")(trade_menu)
dp.callback_query(lambda c: c.data == "arb_usdc")(arb_usdc)
dp.message(StateFilter(TradeStates.arb_amount))(arb_amount)
dp.callback_query(lambda c: c.data == "withdraw")(withdraw_menu)
dp.message(StateFilter(TradeStates.withdraw_process))(withdraw_process)
dp.message(Command("copy"))(copy_setup)
dp.callback_query(lambda c: c.data == "restart")(restart)

async def restart(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await trade_start(callback.message, state)
    logger.info(f"User {callback.from_user.id} restarted bot")

async def main():
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())