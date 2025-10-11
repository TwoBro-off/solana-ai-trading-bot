import httpx
import json

async def call_solana_rpc(url: str, method: str, params: list = None):
    import time
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params if params else []
    }
    start = time.time()
    async with httpx.AsyncClient(timeout=0.8) as client:
        try:
            response = await client.post(url, headers=headers, content=json.dumps(payload))
            response.raise_for_status()
            latency = (time.time() - start) * 1000
            print(f"RPC {method} latency: {latency:.1f}ms")
            return response.json()
        except Exception as exc:
            print(f"RPC {method} error: {exc}")
            return None

async def get_latest_blockhash(rpc_url: str):
    response = await call_solana_rpc(rpc_url, "getRecentBlockhash")
    if response and 'result' in response and 'value' in response['result']:
        return response['result']['value']['blockhash']
    return None

async def get_token_supply(rpc_url: str, token_mint_address: str):
    response = await call_solana_rpc(rpc_url, "getTokenSupply", [token_mint_address])
    if response and 'result' in response and 'value' in response['result']:
        return response['result']['value']['uiAmountString']
    return None

async def get_token_holders(rpc_url: str, token_mint_address: str):
    # This is a simplified example. Getting all token holders can be complex and resource-intensive.
    # For a real bot, you might need to use a specialized API or iterate through pages.
    # Pour optimiser, utiliser un indexer ou batcher les requêtes si possible
    response = await call_solana_rpc(rpc_url, "getTokenAccountsByOwner", [
        "11111111111111111111111111111111",
        {"mint": token_mint_address},
        {"encoding": "jsonParsed"}
    ])
    if response and 'result' in response and 'value' in response['result']:
        return response['result']['value']
    return None

async def get_account_info(rpc_url: str, public_key: str):
    response = await call_solana_rpc(rpc_url, "getAccountInfo", [
        public_key,
        {"encoding": "jsonParsed"}
    ])
    if response and 'result' in response and 'value' in response['result']:
        return response['result']['value']
    return None