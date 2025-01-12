import logging
from websocket import create_connection

# Configure logging
logging.basicConfig(level=logging.INFO)

# Replace with your project ID
PROJECT_ID = "bfdee2a88917a9e26b82aef708214be7"
RELAY_URL = f"wss://relay.walletconnect.org?projectId={PROJECT_ID}"

def test_relay_connection():
    """
    Test WebSocket connection to WalletConnect relay.
    """
    try:
        logging.info(f"Connecting to {RELAY_URL}")
        ws = create_connection(RELAY_URL)
        logging.info("✅ WebSocket connection established successfully.")
        ws.close()
    except Exception as e:
        logging.error(f"❌ WebSocket error: {e}")

# Run the test
if __name__ == "__main__":
    test_relay_connection()
