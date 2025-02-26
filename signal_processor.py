from stellar_sdk import Asset, ChangeTrust, PathPaymentStrictSend
from utils import load_keypair, build_transaction
from stellar_utils import server
from trade import has_trustline

async def process_signal(signal: dict, telegram_id: int, db_pool):
    """Handle manual buy/sell signals."""
    keypair = await load_keypair(telegram_id, db_pool)
    account = server.load_account(keypair.public_key)
    action = signal["action"]  # "buy" or "sell"
    asset = Asset(signal["asset"]["code"], signal["asset"]["issuer"])
    amount = signal["amount"]
    
    operations = []
    if not has_trustline(account, asset):  # Assuming has_trustline is imported
        operations.append(ChangeTrust(asset=asset, limit="1000.0"))
    
    if action == "buy":
        operations.append(PathPaymentStrictSend(send_asset=Asset.native(), send_amount="101", destination=keypair.public_key, dest_asset=asset, dest_min=amount, path=[Asset.native(), asset]))
    elif action == "sell":
        operations.append(PathPaymentStrictSend(send_asset=asset, send_amount=amount, destination=keypair.public_key, dest_asset=Asset.native(), dest_min="100", path=[asset, Asset.native()]))
    
    tx = await build_transaction(account, keypair, operations)
    response = server.submit_transaction(tx)
    return f"{action.capitalize()} {amount} {asset.code} executed. Tx: {response['hash']}", response["hash"]