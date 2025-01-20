import requests

def get_user_wallet(telegram_id):
    backend_url = "http://localhost:4000/link-wallet"  # Replace with your backend endpoint
    response = requests.post(backend_url, json={"telegramId": telegram_id})
    
    if response.status_code == 200:
        data = response.json()
        return data.get("walletAddress"), data.get("sessionTopic")
    else:
        print(f"Error fetching wallet for Telegram ID {telegram_id}: {response.text}")
        return None, None
