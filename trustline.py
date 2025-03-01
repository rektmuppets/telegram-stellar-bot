from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from cryptography.fernet import Fernet

horizon = Server("https://horizon-testnet.stellar.org")
with open("bot_key.enc", "rb") as f:
    enc = f.read()
cipher = Fernet("Tm_TTIwsP54Jr5GO-swnJlOmYm7YD7Pa2y9h31uoPvQ=")
secret = cipher.decrypt(enc).decode()
kp = Keypair.from_secret(secret)
acct = horizon.load_account(kp.public_key)
tx = TransactionBuilder(acct, Network.TESTNET_NETWORK_PASSPHRASE, 100)\
    .append_change_trust_op(
        asset=Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")  # AnchorUSD
    ).build()
tx.sign(kp)
horizon.submit_transaction(tx)
print("Trustline added!")