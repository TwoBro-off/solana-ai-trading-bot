"""
Module: blockchain/manager.py
Description: Abstraction multi-blockchain (Solana, EVM, BSC, etc.) pour scan, buy, sell, balance.
"""
from typing import Any, Dict

class BlockchainManager:
    def __init__(self, blockchain: str, rpc_url: str = None, private_key: str = None):
        self.blockchain = blockchain.lower()
        self.rpc_url = rpc_url
        self.private_key = private_key
        if self.blockchain == "solana":
            from .solana_adapter import SolanaAdapter
            self.adapter = SolanaAdapter(rpc_url, private_key)
        elif self.blockchain in ("evm", "ethereum", "bsc", "binance"):  # EVM chains
            from .evm_adapter import EVMAdapter
            self.adapter = EVMAdapter(rpc_url, private_key)
        else:
            raise ValueError(f"Blockchain non supportée: {blockchain}")

    async def scan_tokens(self, *args, **kwargs) -> Any:
        return await self.adapter.scan_tokens(*args, **kwargs)

    async def buy(self, token_address: str, amount: float, **kwargs) -> Dict:
        return await self.adapter.buy(token_address, amount, **kwargs)

    async def sell(self, token_address: str, amount: float, **kwargs) -> Dict:
        return await self.adapter.sell(token_address, amount, **kwargs)

    async def get_balance(self, wallet: str) -> float:
        return await self.adapter.get_balance(wallet)

    async def get_token_info(self, token_address: str) -> Dict:
        return await self.adapter.get_token_info(token_address)
