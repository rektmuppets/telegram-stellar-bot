import sqlite3
import random

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
        print(f"Decrypted secret: {secret}")  # Debug: Should be SB...
        keypair = Keypair.from_secret(secret)
        print(f"Keypair type: {type(keypair)}, public_key: {keypair.public_key}")  # Debug: Should be Keypair object
        return keypair