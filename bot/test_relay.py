import requests

def test_walletconnect_relay(project_id, api_key):
    """
    Test connection to WalletConnect relay and validate the project setup.
    """
    url = f"https://relay.walletconnect.com/v1?projectId={project_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("✅ Relay is active and reachable.")
            print(f"Response: {response.json()}")
        else:
            print(f"⚠️ Relay returned status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error connecting to WalletConnect relay: {e}")

# Replace with your project ID and API Key
project_id = "bfdee2a88917a9e26b82aef708214be7"
api_key = "c0a1c1e4-83db-4d0a-9322-483fa104f3ec"  # Corrected by enclosing in quotes

# Run the test
test_walletconnect_relay(project_id, api_key)
