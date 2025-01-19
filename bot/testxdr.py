from stellar_sdk import TransactionEnvelope, Network, Keypair
import base64

# Fix padding for Base64-encoded string
def fix_padding(xdr_string):
    missing_padding = len(xdr_string) % 4
    if missing_padding:
        xdr_string += "=" * (4 - missing_padding)
    return xdr_string

# Replace with your signed XDR, user's public key, and server's public key
signed_xdr = "AAAAAgAAAAAZif61Pl7YWWjFZnBuDdG7fO6mBJJ4kZmQgPdrwH2ANQAAAMgABrTFAAAAAQAAAAEAAAAAAAAAAAAAAABnfLUbAAAAAAAAAAIAAAAAAAAACgAAAA93ZWJfYXV0aF9kb21haW4AAAAAAQAAAAtzdGVsbGFyLm9yZwAAAAAAAAAACgAAAA1jbGllbnRfZG9tYWluAAAAAAAAAQAAAAt0ZXN0X2NsaWVudAAAAAAAAAAAAsB9gDUAAABANmHzjCt7sh9P3Xxb8zTtyBvrCNzLmdl88EAsk6lj45VBSW/Y7PA46EoFkNuCR33casmEk0jGlhNKLLH0CCI5Af0Pu4kAAABAxxFGqdFe+zGG1tmQhwEwdcO/DtbMs58RQvyIqEIIvxIXRqDgrhR2llb+yIzFW2LYF9K6G3pSDBf11kYUb7vrBw=="
user_public_key = "GDU2AXFKSS7MQ5LTHA56AHC2P33VGVXVZCXLZPZWPFCS2GX5B65YSTZO"
server_public_key = "GAMYT7VVHZPNQWLIYVTHA3QN2G5XZ3VGASJHREMZSCAPO26APWADKREC"

# Fix padding for the signed XDR
signed_xdr = fix_padding(signed_xdr)

# Load the signed envelope
try:
    envelope = TransactionEnvelope.from_xdr(signed_xdr, Network.TESTNET_NETWORK_PASSPHRASE)
except Exception as e:
    print(f"Error loading XDR: {e}")
    exit()

# Hash of the transaction
transaction_hash = envelope.hash()

# Track which signatures are verified
verified_signatures = {"user": False, "server": False}

# Verify each signature
for signature in envelope.signatures:
    print(f"Checking a signature...")

    try:
        # Check against the user's public key
        if not verified_signatures["user"]:
            Keypair.from_public_key(user_public_key).verify(transaction_hash, signature.signature)
            print("User signature is valid!")
            verified_signatures["user"] = True
    except Exception as e:
        print(f"User signature verification failed: {e}")

    try:
        # Check against the server's public key
        if not verified_signatures["server"]:
            Keypair.from_public_key(server_public_key).verify(transaction_hash, signature.signature)
            print("Server signature is valid!")
            verified_signatures["server"] = True
    except Exception as e:
        print(f"Server signature verification failed: {e}")

    # Stop checking once both signatures are verified
    if verified_signatures["user"] and verified_signatures["server"]:
        break

# Final validation results
if verified_signatures["user"] and verified_signatures["server"]:
    print("Both user and server signatures are valid!")
elif not verified_signatures["user"]:
    print("User signature is missing or invalid.")
elif not verified_signatures["server"]:
    print("Server signature is missing or invalid.")
