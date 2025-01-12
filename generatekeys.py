from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def generate_ed25519_keypair():
    # Generate private key
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Export private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    print("Private Key (PEM):")
    print(private_key_pem.decode('utf-8'))

    # Export public key as raw bytes
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    public_key_hex = public_key_bytes.hex()
    print("\nPublic Key (Hex):")
    print(public_key_hex)

    return private_key_pem, public_key_hex

# Generate and print keys
private_key, public_key = generate_ed25519_keypair()
