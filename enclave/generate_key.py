from stellar_sdk import Keypair
from cryptography.fernet import Fernet
import os
import sys

print("Starting key generation...")
sys.stdout.flush()

kp = Keypair.random()
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)
encrypted_secret = cipher.encrypt(kp.secret.encode())
# Use current dir, not hardcode /app
output_file = os.path.join(os.getcwd(), "bot_key.enc")
with open(output_file, "wb") as f:
    f.write(encrypted_secret)
print(f"Bot Public Key: {kp.public_key}")
print(f"Encryption Key (save this!): {encryption_key.decode()}")
sys.stdout.flush()