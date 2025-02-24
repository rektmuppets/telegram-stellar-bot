import time
from stellar_sdk import Server, TransactionBuilder, Network, Asset, Keypair

server = Server("https://horizon-testnet.stellar.org")
TESTNET = Network.TESTNET_NETWORK_PASSPHRASE

async def build_transaction(source_account, keypair: Keypair, operations: list, memo=None, base_fee=100):
    try:
        tx_builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=TESTNET,
            base_fee=base_fee,
        )
        tx_builder = tx_builder.add_time_bounds(min_time=0, max_time=int(time.time()) + 900)
        for operation in operations:
            tx_builder = tx_builder.append_operation(operation)
        if memo:
            tx_builder = tx_builder.add_text_memo(memo)  # Add memo before building
        tx = tx_builder.build()
        tx.sign(keypair)
        print(f"Built transaction sequence: {tx.transaction.sequence}, XDR: {tx.to_xdr()}")
        return tx
    except Exception as e:
        raise Exception(f"Failed to build transaction: {str(e)}")