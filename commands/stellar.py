import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Signer

# Create a router for Stellar commands
router = Router()

# Server for Stellar Testnet
server = Server("https://horizon-testnet.stellar.org")

# In-memory storage for user data
user_keys = {}

# Validate Stellar public key
def is_valid_public_key(public_key):
    try:
        Keypair.from_public_key(public_key)  # This validates the format
        return True
    except Exception as e:
        logging.error(f"Invalid public key: {public_key}, Error: {e}")
        return False

# Command: /register
@router.message(Command("register"))
async def register_command(message: Message):
    try:
        user_data = user_keys.get(message.from_user.id)
        if not user_data or not user_data.get("verified"):
            await message.answer("You must verify your account first using /verify.")
            return

        public_key = user_data["public_key"]
        passkey = Keypair.random()
        user_keys[message.from_user.id]["passkey"] = passkey

        # Fetch user account
        account = server.load_account(public_key)

        # Create a transaction to add the passkey as a signer
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            )
            .append_set_options_op(
                signer=Signer.ed25519_public_key(passkey.public_key, 1),  # Low weight signer
            )
            .set_timeout(300)
            .build()
        )

        # Send transaction to user for signing
        await message.answer(
            f"Sign this transaction to add the passkey as a signer:\n\n{transaction.to_xdr()}"
        )
    except Exception as e:
        logging.error(f"Error in /register: {e}")
        await message.answer("An error occurred while registering. Please try again.")

# Command: /balance
@router.message(Command("balance"))
async def balance_command(message: Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Usage: /balance <public_key>")
            return

        public_key = args[1]
        if not is_valid_public_key(public_key):
            await message.answer("Invalid Stellar public key.")
            return

        # Fetch account balances from Stellar Testnet
        try:
            account = server.accounts().account_id(public_key).call()
            balances = account["balances"]
            balance_text = "\n".join(
                f"{balance['asset_type'] if balance['asset_type'] == 'native' else balance['asset_code']}: {balance['balance']}"
                for balance in balances
            )
            await message.answer(f"Your balance:\n{balance_text}")
        except Exception as e:
            logging.error(f"Account fetch error: {e}")
            await message.answer("Error: Account not found on the Stellar Testnet.")
    except Exception as e:
        logging.error(f"Error in /balance: {e}")
        await message.answer(f"An error occurred: {e}")

# Register Stellar commands
def register_stellar_commands(dp):
    dp.include_router(router)
