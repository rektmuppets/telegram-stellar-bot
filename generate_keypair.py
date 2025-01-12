from stellar_sdk import Keypair

# Generate a random keypair
keypair = Keypair.random()

# Print the public and secret keys
print("Public Key:", keypair.public_key)
print("Secret Key:", keypair.secret)
