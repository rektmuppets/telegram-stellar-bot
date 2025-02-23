import time
from stellar_sdk import Server, TransactionBuilder, Network, Asset, Keypair

server = Server("https://horizon-testnet.stellar.org")
TESTNET = Network.TESTNET_NETWORK_PASSPHRASE

async def build_transaction(source_account, keypair: Keypair, operations: list, base_fee: int = 100):
    """
    Build and sign a Stellar transaction with dynamic operations.
    
    Args:
        source_account: Loaded account object from server.load_account()
        keypair: Keypair object for signing the transaction
        operations: List of operation objects (e.g., Payment, ChangeTrust)
        base_fee: Base fee per operation (default: 100 stroops)
    
    Returns:
        Signed TransactionEnvelope ready for submission
    """
    try:
        # Initialize the TransactionBuilder with common settings
        tx_builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=TESTNET,
            base_fee=base_fee,
        )
        
        # Add time bounds (15-minute validity window)
        tx_builder = tx_builder.add_time_bounds(min_time=0, max_time=int(time.time()) + 900)
        
        # Dynamically append all operations from the list
        for operation in operations:
            tx_builder = tx_builder.append_operation(operation)
        
        # Build the transaction
        tx = tx_builder.build()
        
        # Sign the transaction with the provided keypair
        tx.sign(keypair)
        
        return tx
    
    except Exception as e:
        raise Exception(f"Failed to build transaction: {str(e)}")