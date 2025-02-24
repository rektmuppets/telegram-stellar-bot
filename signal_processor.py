import json
from stellar_sdk import Asset, Payment, ChangeTrust, TextMemo
from stellar_utils import build_transaction, server
from utils import load_keypair

async def process_signal(signal: dict, telegram_id: int, db_pool):
    """Process an incoming copy trade signal and execute the transaction."""
    try:
        keypair = await load_keypair(telegram_id, db_pool)
        account = server.load_account(keypair.public_key)
        
        action = signal.get("action")
        asset_code = signal["asset"]["code"]
        asset_issuer = signal["asset"]["issuer"]
        amount = signal["amount"]
        destination = signal["destination"]
        memo = signal.get("memo")
        
        trade_asset = Asset(code=asset_code, issuer=asset_issuer)
        operations = []
        if action in ("trade", "trust_only"):
            operations.append(ChangeTrust(asset=trade_asset, limit="1000.0"))
        if action == "trade":
            operations.append(Payment(destination=destination, asset=trade_asset, amount=amount))
        
        if not operations:
            return f"Unknown action: {action}", None
        
        tx = await build_transaction(account, keypair, operations)
        if memo:
            tx.transaction.memo = TextMemo(memo)
            tx.sign(keypair)
        
        response = server.submit_transaction(tx)
        return f"Processed signal {signal['signal_id']}: {action} {amount} {asset_code}", response["hash"]
    except Exception as e:
        return f"Signal processing failed: {str(e)}", None

async def mock_signal_test(telegram_id: int, db_pool):
    """Test function for a mock signal."""
    mock_signal = {
        "signal_id": "12345",
        "action": "trade",
        "asset": {"code": "USDC", "issuer": "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"},
        "amount": "100.50",
        "destination": "GAW56XMB3ECEDW4MV7HHCPOCFUCZSONS7ZOYQLVYR7E4537E3D4YJNDN",
        "memo": "CopyTrade12345",
        "timestamp": "2025-02-22T10:00:00Z"
    }
    return await process_signal(mock_signal, telegram_id, db_pool)