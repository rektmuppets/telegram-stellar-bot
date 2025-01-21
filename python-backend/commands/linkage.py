import os
import requests

# Load environment variables for API endpoints
LINK_WALLET_URL = os.getenv("LINK_WALLET_URL", "https://api.photonbot.xyz/link-wallet")

def get_user_wallet(telegram_id):
    response = requests.post(LINK_WALLET_URL, json={"telegramId": telegram_id})
    
    if response.status_code == 200:
        data = response.json()
        return data.get("walletAddress"), data.get("sessionTopic")
    else:
        print(f"Error fetching wallet for Telegram ID {telegram_id}: {response.text}")
        return None, None
