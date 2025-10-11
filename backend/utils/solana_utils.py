import time
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.keypair import Keypair
from loguru import logger
import base58

async def get_solana_balance(rpc_url: str, private_key: str) -> float:
    """Retourne le solde SOL du wallet (sécurisé, optimisé)."""
    client = Client(rpc_url)
    try:
        try:
            payer = Keypair.from_secret_key(base58.b58decode(private_key))
        except ValueError:
            payer = Keypair.from_secret_key(bytes.fromhex(private_key))
        balance_response = client.get_balance(payer.public_key)
        if balance_response and 'result' in balance_response and 'value' in balance_response['result']:
            balance_lamports = balance_response['result']['value']
            balance_sol = balance_lamports / 1_000_000_000
            return balance_sol
        else:
            logger.error(f"Failed to get balance: {balance_response}")
            return 0.0
    except Exception as e:
        logger.error(f"Error getting Solana balance: {e}")
        return 0.0

async def get_rpc_latency(rpc_url: str) -> float:
    """Mesure la latence RPC (optimisé)."""
    import time
    start = time.time()
    try:
        client = Client(rpc_url)
        client.get_slot()
        latency = (time.time() - start) * 1000
        return latency
    except Exception as e:
        logger.error(f"Error measuring RPC latency: {e}")
        return -1.0