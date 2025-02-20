from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

def load_keypair():
    load_dotenv()  # Load here too
    with open("bot_key.enc", "rb") as f:
        encrypted_secret = f.read()
    cipher = Fernet(os.getenv("ENCRYPTION_KEY"))
    secret = cipher.decrypt(encrypted_secret).decode()
    from stellar_sdk import Keypair
    return Keypair.from_secret(secret)

async def get_x_sentiment(asset_code):
    import random
    return random.uniform(-1, 1)