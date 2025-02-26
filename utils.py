import sqlite3
import random
from stellar_sdk import Server, Asset

server = Server("https://horizon-testnet.stellar.org")

def init_db():
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS copy_trading (wallet_address TEXT PRIMARY_KEY)")
    conn.commit()
    conn.close()

def list_copy_wallets():
    conn = sqlite3.connect("copy_trading.db")
    c = conn.cursor()
    c.execute("SELECT wallet_address FROM copy_trading")
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
        if len(parts) == 2:  # Format: "USDC:GBBD47..."
            return Asset(parts[0], parts[1])
        elif len(parts) == 3 and parts[0] in ["credit_alphanum4", "credit_alphanum12"]:
            return Asset(parts[1], parts[2])
    return None

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
        print(f"Decrypted secret: {secret}")  # Debug: Should be SB...remove this its security risk
        keypair = Keypair.from_secret(secret)
        print(f"Keypair type: {type(keypair)}, public_key: {keypair.public_key}")  # Debug: Should be Keypair object
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
            # Use asset_type, asset_code, asset_issuer for dest_asset
            dest_asset = parse_asset({
                "type": op.get("asset_type", "native"),  # Changed from destination_asset_type
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