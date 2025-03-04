import time
import sqlite3
import random
import asyncio
import requests
from stellar_sdk import Server, Asset, Payment, ChangeTrust, PathPaymentStrictSend, PathPaymentStrictReceive
from stellar_utils import build_transaction, server, TESTNET
from aiogram import types, Dispatcher, Bot
from globals import shutdown_flag

server = Server("https://horizon-testnet.stellar.org")
shutdown_flag = asyncio.Event()

def init_db():
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    
    # Check existing tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in c.fetchall()}
    
    # Initialize or update copy_trading table
    if "copy_trading" not in tables:
        c.execute("""
            CREATE TABLE copy_trading (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wallet_address TEXT,
                status TEXT DEFAULT 'active',
                multiplier REAL DEFAULT 1.0,
                fixed_amount REAL,
                UNIQUE(user_id, wallet_address)
            )
        """)
    else:
        # Add missing columns to existing table
        c.execute("PRAGMA table_info(copy_trading)")
        columns = {col[1] for col in c.fetchall()}
        if "user_id" not in columns:
            c.execute("ALTER TABLE copy_trading ADD COLUMN user_id INTEGER")
        if "status" not in columns:
            c.execute("ALTER TABLE copy_trading ADD COLUMN status TEXT DEFAULT 'active'")
        if "multiplier" not in columns:
            c.execute("ALTER TABLE copy_trading ADD COLUMN multiplier REAL DEFAULT 1.0")
        if "fixed_amount" not in columns:
            c.execute("ALTER TABLE copy_trading ADD COLUMN fixed_amount REAL")
    
    # Initialize user_settings table
    if "user_settings" not in tables:
        c.execute("""
            CREATE TABLE user_settings (
                user_id INTEGER PRIMARY KEY,
                slippage REAL DEFAULT 0.05
            )
        """)
    
    conn.commit()
    conn.close()

def list_copy_wallets(telegram_id):
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT wallet_address FROM copy_trading WHERE user_id = ?", (telegram_id,))
    wallets = [row[0] for row in c.fetchall()]
    conn.close()
    return wallets    

def parse_asset(asset_data):
    """Parse an asset from a dictionary or string."""
    if isinstance(asset_data, dict):
        asset_type = asset_data.get("type", asset_data.get("asset_type"))
        if asset_type == "native":
            return Asset.native()
        return Asset(asset_data.get("code", asset_data.get("asset_code")),
                     asset_data.get("issuer", asset_data.get("asset_issuer")))
    elif isinstance(asset_data, str):
        if asset_data == "native":
            return Asset.native()
        parts = asset_data.split(":")
        if len(parts) == 2:
            return Asset(parts[0], parts[1])
        elif len(parts) == 3 and parts[0] in ["credit_alphanum4", "credit_alphanum12"]:
            return Asset(parts[1], parts[2])
    return None

def get_trustline_limit(account, asset):
    """Get the current trustline limit for an asset in an account."""
    for balance in account.raw_data["balances"]:
        if (not asset.is_native() and
            balance["asset_type"] != "native" and
            balance["asset_code"] == asset.code and
            balance["asset_issuer"] == asset.issuer):
            return float(balance.get("limit", 0))  # 0 if no limit (unlimited, rare)
    return 0  # No trustline exists

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

async def get_x_sentiment(asset_code):
    return random.uniform(-1, 1)

async def load_keypair(telegram_id, db_pool):
    from cryptography.fernet import Fernet
    from stellar_sdk import Keypair
    async with db_pool.acquire() as conn:
        user_data = await conn.fetchrow("SELECT encrypted_secret, encryption_key FROM users WHERE telegram_id = $1", telegram_id)
        if not user_data:
            raise ValueError("User not registered")
        encrypted_secret = bytes.fromhex(user_data["encrypted_secret"])
        cipher = Fernet(user_data["encryption_key"].encode())
        secret = cipher.decrypt(encrypted_secret).decode()
        print(f"Decrypted secret: {secret}")  # Debug: Remove in production
        keypair = Keypair.from_secret(secret)
        print(f"Keypair type: {type(keypair)}, public_key: {keypair.public_key}")
        return keypair

async def fetch_copy_trades(wallet_address):
    transactions = server.transactions().for_account(wallet_address).order(desc=True).limit(10).call()
    for tx in transactions["_embedded"]["records"]:
        operations = server.operations().for_transaction(tx["id"]).call()
        for op in operations["_embedded"]["records"]:
            if op["type"] not in ["path_payment_strict_send", "path_payment_strict_receive"]:
                print(f"Skipping unsupported operation type: {op['type']} in tx {tx['id']}")
                continue
            
            print(f"Processing operation: {op}")
            
            send_asset = parse_asset({
                "type": op.get("source_asset_type", "native"),
                "code": op.get("source_asset_code"),
                "issuer": op.get("source_asset_issuer")
            })
            dest_asset = parse_asset({
                "type": op.get("asset_type", "native"),
                "code": op.get("asset_code"),
                "issuer": op.get("asset_issuer")
            })
            path = [parse_asset(p) for p in op.get("path", [])]

            if not send_asset or not dest_asset:
                print(f"Failed to parse assets: send_asset={send_asset}, dest_asset={dest_asset}")
                continue

            effects = server.effects().for_operation(op["id"]).call()
            originator_account = wallet_address
            send_amount = None
            dest_amount = None
            print(f"Effects for op {op['id']}: {effects['_embedded']['records']}")
            for effect in effects["_embedded"]["records"]:
                if effect["account"] != originator_account:
                    continue
                if effect["type"] in ["account_debited", "account_credited"]:
                    effect_asset = parse_asset({
                        "type": effect.get("asset_type"),
                        "code": effect.get("asset_code"),
                        "issuer": effect.get("asset_issuer")
                    })
                    if not effect_asset:
                        print(f"Could not parse effect asset: {effect}")
                        continue
                    if effect["type"] == "account_debited" and effect_asset == send_asset:
                        send_amount = effect["amount"]
                    elif effect["type"] == "account_credited" and effect_asset == dest_asset:
                        dest_amount = effect["amount"]
                elif effect["type"] == "liquidity_pool_trade":
                    continue

            if op["type"] == "path_payment_strict_send":
                send_amount = send_amount or op.get("send_amount")
                dest_amount = dest_amount or op.get("amount")
            else:
                dest_amount = dest_amount or op.get("dest_amount")
                send_amount = send_amount or op.get("source_amount")

            if not (send_amount and dest_amount):
                print(f"Missing amounts after fallback: send={send_amount}, dest={dest_amount}")
                continue

            trade = {
                "signal_id": tx["id"],
                "action": "trade",
                "operation_type": op["type"],
                "send_asset": {"code": send_asset.code or "XLM", "issuer": send_asset.issuer},
                "send_amount": send_amount,
                "dest_asset": {"code": dest_asset.code or "XLM", "issuer": dest_asset.issuer},
                "dest_amount": dest_amount,
                "path": [{"code": p.code or "XLM", "issuer": p.issuer} for p in path],
                "timestamp": tx["created_at"],
            }
            print(f"Trade constructed: {trade}")
            return trade
    print(f"No recent path payment trades found for {wallet_address}")
    return None

async def async_stream_transactions(wallet):
    """Stream transactions asynchronously with persistent connection."""
    async def stream_generator():
        loop = asyncio.get_event_loop()
        retry_delay_min = 0.1  # Faster retry
        retry_delay_max = 2.0  # Cap delay
        max_retries = 10
        retries = 0
        
        stream = None
        try:
            stream = server.transactions().for_account(wallet).cursor("now").stream()
            print(f"Started streaming for {wallet}")
            
            while not shutdown_flag.is_set():
                try:
                    tx = await asyncio.wait_for(
                        loop.run_in_executor(None, next, stream),
                        timeout=60
                    )
                    retries = 0
                    yield tx
                except (asyncio.TimeoutError, requests.exceptions.ConnectionError) as e:
                    retries += 1
                    delay = min(retry_delay_min * retries, retry_delay_max)  # Exponential backoff, capped
                    print(f"Stream timeout or connection error for {wallet}: {str(e)}, retrying in {delay:.1f} seconds (retry {retries}/{max_retries})...")
                    if retries > max_retries:
                        print(f"Max retries exceeded for {wallet}, stopping stream.")
                        break
                    await asyncio.sleep(delay)
                    break  # Reconnect
                except StopIteration:
                    print(f"Stream stopped for {wallet}, reconnecting...")
                    break
                except Exception as e:
                    retries += 1
                    delay = min(retry_delay_min * retries, retry_delay_max)
                    print(f"Unexpected stream error for {wallet}: {str(e)}, retrying in {delay:.1f} seconds (retry {retries}/{max_retries})...")
                    if retries > max_retries:
                        print(f"Max retries exceeded for {wallet}, stopping stream.")
                        break
                    await asyncio.sleep(delay)
                    break
        except Exception as e:
            retries += 1
            delay = min(retry_delay_min * retries, retry_delay_max)
            print(f"Stream setup error for {wallet}: {str(e)}, retrying in {delay:.1f} seconds (retry {retries}/{max_retries})...")
            if retries > max_retries:
                print(f"Max retries exceeded for {wallet}, stopping stream.")
            else:
                await asyncio.sleep(delay)
                await stream_generator()  # Recurse to reconnect
        finally:
            if stream is not None:
                try:
                    stream.close()
                except:
                    pass
        print(f"Stream ended for wallet {wallet}")

    return stream_generator()

# In utils.py
async def copy_trading_stream(chat_id: int, telegram_id: int, dp: Dispatcher, bot: Bot, db_pool):
    print(f"Starting streaming for telegram_id: {telegram_id}, chat_id: {chat_id}")
    while not shutdown_flag.is_set():
        try:
            conn = sqlite3.connect("copy_trading.db")
            c = conn.cursor()
            c.execute("SELECT wallet_address FROM copy_trading WHERE user_id = ? AND status = 'active'", (telegram_id,))
            wallets = [row[0] for row in c.fetchall()]
            conn.close()
            
            print(f"Active wallets: {wallets}")
            if not wallets:
                await bot.send_message(chat_id, "No active wallets to stream. Add with /addcopy or resume in /copytrade_menu.")
                await asyncio.sleep(60)
                continue
            
            tasks = [asyncio.create_task(stream_wallet(wallet, chat_id, telegram_id, dp, bot, db_pool)) for wallet in wallets]
            print(f"Streaming tasks created: {len(tasks)}")
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Streaming error: {e}, reconnecting in 5 seconds...")
            await bot.send_message(chat_id, f"Streaming error: {e}. Retrying...")
            await asyncio.sleep(5)
            continue

async def stream_wallet(wallet: str, chat_id: int, telegram_id: int, dp: Dispatcher, bot: Bot, db_pool):
    print(f"Started streaming for {wallet}")
    stream_iter = await async_stream_transactions(wallet)
    async for tx in stream_iter:
        if shutdown_flag.is_set():
            break
        trade = await fetch_copy_trades(wallet)
        if trade and trade["signal_id"] == tx["id"]:
            conn = sqlite3.connect("copy_trading.db")
            c = conn.cursor()
            c.execute("SELECT multiplier, fixed_amount FROM copy_trading WHERE user_id = ? AND wallet_address = ?", (telegram_id, wallet))
            settings = c.fetchone()
            conn.close()
            multiplier = settings[0] if settings else 1.0
            fixed_amount = settings[1] if settings else None
            await process_api_signal(None, trade, db_pool, telegram_id, dp, chat_id=chat_id, bot=bot, multiplier=multiplier, fixed_amount=fixed_amount)

async def process_api_signal(message: types.Message | None, signal: dict, db_pool, telegram_id: int = None, dp=None, chat_id: int = None, bot=None, multiplier=1.0, fixed_amount=None):
    telegram_id = message.from_user.id if message else telegram_id
    if not telegram_id:
        print("No valid telegram_id provided for streaming")
        return
    
    signal_id = signal["signal_id"]
    if hasattr(process_api_signal, 'processed_signals') and signal_id in process_api_signal.processed_signals:
        print(f"Skipping duplicate signal: {signal_id}")
        return
    if not hasattr(process_api_signal, 'processed_signals'):
        process_api_signal.processed_signals = set()
    process_api_signal.processed_signals.add(signal_id)
    
    try:
        if db_pool is None:
            error_msg = "Database pool is not initialized"
            if message:
                await message.reply(error_msg)
            elif bot and chat_id:
                await bot.send_message(chat_id, error_msg)
            print(error_msg)
            return
        
        keypair = await load_keypair(telegram_id, db_pool)
        print(f"Decrypted secret: {keypair.secret}")
        print(f"Keypair type: {type(keypair)}, public_key: {keypair.public_key}")
        
        operation_type = signal["operation_type"]
        if operation_type not in ["path_payment_strict_send", "path_payment_strict_receive"]:
            error_msg = f"Unsupported operation type: {operation_type}"
            if message:
                await message.reply(error_msg)
            elif bot and chat_id:
                await bot.send_message(chat_id, error_msg)
            print(error_msg)
            return

        send_asset = parse_asset(signal["send_asset"])
        dest_asset = parse_asset(signal["dest_asset"])
        send_amount = float(signal["send_amount"])
        dest_amount = float(signal["dest_amount"])
        
        if fixed_amount:
            send_amount = float(fixed_amount)
        else:
            send_amount *= multiplier
        
        account = server.load_account(keypair.public_key)
        dest_min = round(dest_amount * multiplier * 0.99, 7)
        transaction = await build_transaction(
            source_account=account,
            keypair=keypair,
            operations=[
                PathPaymentStrictSend(
                    destination=keypair.public_key,
                    send_asset=send_asset,
                    send_amount=str(send_amount),
                    dest_asset=dest_asset,
                    dest_min=str(dest_min),
                    path=signal["path"]
                ) if operation_type == "path_payment_strict_send" else
                PathPaymentStrictReceive(
                    destination=keypair.public_key,
                    send_asset=send_asset,
                    send_max=str(send_amount),
                    dest_asset=dest_asset,
                    dest_amount=str(dest_amount * multiplier),
                    path=signal["path"]
                )
            ]
        )
        
        signed_transaction = transaction
        xdr_snippet = signed_transaction.to_xdr()[:50]  # Truncate for readability
        print(f"Built transaction sequence: {account.sequence}, XDR: {xdr_snippet}...")
        
        response = server.submit_transaction(signed_transaction)
        success_msg = (
            f"Copied {operation_type}\n"
            f"From: {keypair.public_key[:8]}...\n"
            f"Amount: {send_amount} {send_asset.code} -> {dest_amount} {dest_asset.code}\n"
            f"Signal ID: {signal_id[:8]}...\n"
            f"XDR: {xdr_snippet}..."
        )
        if message:
            await message.reply(success_msg)
        elif bot and chat_id:
            await bot.send_message(chat_id, success_msg)
        print(success_msg)
    except Exception as e:
        error_msg = f"Copy trade failed: {str(e)}"
        if message:
            await message.reply(error_msg)
        elif bot and chat_id:
            try:
                await bot.send_message(chat_id, error_msg)
            except Exception as send_error:
                print(f"Failed to send error message: {send_error}")
        print(error_msg)
        return