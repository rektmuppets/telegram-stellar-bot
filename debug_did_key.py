import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Replace this with your Ed25519 private key in PEM format
PRIVATE_KEY_PEM = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIMkYjHGo6xgeV70ncj0jJWRVqki8Kx08qO+b9MV9JPss
-----END PRIVATE KEY-----"""

def load_private_key(pem_data):
    """
    Loads the Ed25519 private key from PEM data.
    """
    return serialization.load_pem_private_key(pem_data, password=None)

def generate_did_key(public_key):
    """
    Generates a DID key using the Base58-encoded Ed25519 public key.
    """
    try:
        did_key_prefix = b'\xed\x01'  # Ed25519 multicodec prefix
        prefixed_key = did_key_prefix + public_key
        did_key = base58.b58encode(prefixed_key).decode('utf-8')
        did = f"did:key:{did_key}"
        print(f"Generated DID key: {did}")
    except Exception as e:
        print(f"Error generating DID key: {e}")

def main():
    private_key = load_private_key(PRIVATE_KEY_PEM)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    print(f"Raw public key: {public_key.hex()}")

    generate_did_key(public_key)

if __name__ == "__main__":
    main()
