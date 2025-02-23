import socket
import json
from stellar_sdk import Keypair
from cryptography.fernet import Fernet

def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 5000))
    server.listen(1)
    print("Mock enclave server running on port 5000...")

    while True:
        try:
            client_sock, addr = server.accept()
            print(f"Connection from {addr}")
            data = client_sock.recv(1024).decode()
            if not data:
                print("No data received")
                client_sock.close()
                continue
            print(f"Received: {data}")
            request = json.loads(data)
            telegram_id = request.get("telegram_id")
            if not telegram_id:
                print("No telegram_id in request")
                client_sock.close()
                continue

            kp = Keypair.random()
            encryption_key = Fernet.generate_key()
            cipher = Fernet(encryption_key)
            encrypted_secret = cipher.encrypt(kp.secret.encode())

            response = {
                "telegram_id": telegram_id,
                "public_key": kp.public_key,
                "encrypted_secret": encrypted_secret.hex(),
                "encryption_key": encryption_key.decode()
            }
            print(f"Sending: {response}")
            client_sock.send(json.dumps(response).encode())
            client_sock.close()
        except Exception as e:
            print(f"Server error: {e}")
            client_sock.close()

if __name__ == "__main__":
    run_server()