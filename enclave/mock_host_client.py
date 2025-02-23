import socket
import json

def request_keypair(telegram_id):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connecting to localhost:5000 for telegram_id: {telegram_id}")
    client.connect(('localhost', 5000))
    request = {"telegram_id": str(telegram_id)}
    print(f"Sending request: {request}")
    client.send(json.dumps(request).encode())
    response_data = client.recv(4096).decode()
    print(f"Received raw data: '{response_data}'")
    if not response_data:
        raise ValueError("No response received from server")
    response = json.loads(response_data)
    client.close()
    return response

if __name__ == "__main__":
    telegram_id = 123456789  # Test user
    try:
        response = request_keypair(telegram_id)
        print(f"Public Key: {response['public_key']}")
        print(f"Encryption Key: {response['encryption_key']}")
    except Exception as e:
        print(f"Client error: {e}")