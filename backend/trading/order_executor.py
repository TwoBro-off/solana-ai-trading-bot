import asyncio
import time
from loguru import logger
import base64
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.rpc.responses import GetBalanceResp # type: ignore
from solders.transaction import Transaction # type: ignore
from solders.pubkey import Pubkey as PublicKey # type: ignore
from solders.keypair import Keypair # type: ignore
from solders.system_program import TransferParams, transfer # type: ignore
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
import base58
import aiohttp

async def get_trustwallet_balance(wallet_address: str, rpc_url: str) -> float:
    """
    Récupère le solde SOL d'un wallet Solana.
    """
    try:
        client = AsyncClient(rpc_url)
        pubkey = PublicKey.from_string(wallet_address)
        balance_response: GetBalanceResp = await client.get_balance(pubkey)
        await client.close()
        return balance_response.value / 1e9  # Convert lamports to SOL
    except Exception as e:
        logger.error(f"Impossible de récupérer le solde pour {wallet_address}: {e}")
        return 0.0


class OrderExecutor:
    """
    Exécute les ordres d'achat/vente sur Solana (simulation ou DEX réel).
    Prêt pour intégration DEX (Orca, Raydium, Jupiter, etc.).
    """

    def __init__(self, rpc_url: str, private_key: str, simulate: bool = True):
        self.rpc_url = rpc_url
        self.client = Client(self.rpc_url) if Client else None
        self.async_client = AsyncClient(self.rpc_url) if AsyncClient else None
        self.simulate = simulate
        self.private_key = private_key
        self.payer = None
        if not self.simulate and self.private_key:
            try:
                self.payer = Keypair.from_secret_key(base58.b58decode(private_key))
                logger.info(f"OrderExecutor initialized in REAL mode for wallet {self.payer.public_key}")
            except Exception as e:
                logger.error(f"Invalid private key. Falling back to simulation mode. Error: {e}")
                self.simulate = True
        
        if self.simulate:
            logger.info(f"OrderExecutor initialized in SIMULATION mode.")

    async def execute_buy(self, token_mint_address: str, amount_sol: float) -> dict:
        """
        Exécute un ordre d'achat (simulation ou réel). Retourne un dict avec succès, latence, txid, message.
        """
        start = time.time()
        if logger:
            logger.info(f"Executing buy order for {amount_sol} SOL worth of token {token_mint_address}")
        try:
            if self.simulate:
                await asyncio.sleep(0)
                if logger:
                    logger.warning("Simulated buy: Actual DEX integration is required here.")
                latency = (time.time() - start) * 1000
                if logger:
                    logger.info(f"Latence achat simulé: {latency:.1f}ms")
                return {"success": True, "latency_ms": latency, "txid": None, "message": "Simulated buy"}
            # --- Intégration DEX réelle ici ---
            if not self.payer or not self.async_client:
                raise Exception("OrderExecutor not configured for real trading (missing payer or async_client).")
            
            txid = await self._buy_on_jupiter(token_mint_address, amount_sol)
            latency = (time.time() - start) * 1000
            return {"success": True, "latency_ms": latency, "txid": txid, "message": "Buy via Jupiter"}
        except NotImplementedError:
            if logger:
                logger.warning("Jupiter buy not implemented, fallback to simulation.")
            await asyncio.sleep(0)
            latency = (time.time() - start) * 1000
            return {"success": True, "latency_ms": latency, "txid": None, "message": "Fallback simulated buy"}
        except Exception as e:
            if logger:
                logger.error(f"Unexpected error in execute_buy: {e}")
            return {"success": False, "latency_ms": None, "txid": None, "message": str(e)}

    async def execute_sell(self, token_mint_address: str, amount_tokens: float) -> dict:
        """
        Exécute un ordre de vente (simulation ou réel). Retourne un dict avec succès, latence, txid, message.
        """
        logger.info(f"Executing sell order for {amount_tokens} of token {token_mint_address}")
        try:
            if self.simulate:
                await asyncio.sleep(0)
                logger.warning("Simulated sell: Actual DEX integration is required here.")
                return {"success": True, "txid": None, "sell_price_sol": 0}

            # --- Intégration DEX réelle ici ---
            if not self.payer or not self.async_client:
                raise Exception("OrderExecutor not configured for real trading (missing payer or async_client).")
            sell_data = await self._sell_on_jupiter(token_mint_address, amount_tokens)
            return {"success": True, **sell_data}

        except NotImplementedError:
            logger.warning("Jupiter sell not implemented, fallback to simulation.")
            await asyncio.sleep(0)
            return {"success": True, "txid": None, "message": "Fallback simulated sell"}
        except Exception as e:
            logger.error(f"Unexpected error in execute_sell: {e}")
            return {"success": False, "latency_ms": None, "txid": None, "message": str(e)}

    async def get_wallet_status(self) -> dict:
        """Vérifie l'état du wallet de trading et retourne son statut."""
        if self.simulate or not self.payer or not self.async_client:
            return {"connected": False, "address": None, "balance_sol": 0, "balance_ok": False, "error": "Not in real mode or payer not set"}

        try:
            balance_sol = await get_trustwallet_balance(str(self.payer.public_key), self.rpc_url)
            return {
                "connected": True,
                "address": str(self.payer.public_key),
                "balance_sol": balance_sol,
                "balance_ok": balance_sol > 0.01 # Seuil minimal pour les frais
            }
        except Exception as e:
            logger.error(f"Could not get wallet balance: {e}")
            return {"connected": False, "address": str(self.payer.public_key), "balance_sol": 0, "balance_ok": False, "error": str(e)}

    async def check_jupiter_api(self) -> bool:
        """Vérifie si l'API de Jupiter est accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                # On teste avec une requête simple qui ne devrait pas échouer
                params = {
                    "inputMint": "So11111111111111111111111111111111111111112",
                    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", # USDC
                    "amount": 10000, # 0.00001 SOL
                    "slippageBps": 50
                }
                async with session.get("https://quote-api.jup.ag/v6/quote", params=params, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Jupiter API health check failed: {e}")
            return False


    async def _buy_on_jupiter(self, token_mint_address: str, amount_sol: float) -> str:
        """
        Achat réel via Jupiter Aggregator (opérationnel).
        """
        if not self.payer:
            raise Exception("Payer keypair not loaded. Cannot execute real trade.")

        logger.info(f"Getting Jupiter quote for buying {amount_sol} SOL of {token_mint_address}")
        sol_mint = "So11111111111111111111111111111111111111112"
        amount_lamports = int(amount_sol * 1e9)

        # See Jupiter doc: https://station.jup.ag/docs/apis/swap-api
        async with aiohttp.ClientSession() as session:
            # 1. Get quote
            quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={sol_mint}&outputMint={token_mint_address}&amount={amount_lamports}&slippageBps=50'
            async with session.get(quote_url, timeout=10) as response:
                response.raise_for_status()
                quote_data = await response.json()
                if 'error' in quote_data:
                    raise Exception(f"Jupiter quote API error: {quote_data['error']}")
            
            # 2. Get swap transaction
            logger.info("Getting swap transaction from Jupiter...")
            swap_payload = {
                "quoteResponse": quote_data,
                "userPublicKey": str(self.payer.public_key),
                "wrapAndUnwrapSol": True,
            }
            async with session.post('https://quote-api.jup.ag/v6/swap', json=swap_payload, timeout=10) as response:
                response.raise_for_status()
                swap_data = await response.json()
                swap_transaction = swap_data.get('swapTransaction')

            # 3. Sign and send transaction
            raw_tx = base64.b64decode(swap_transaction)
            transaction = Transaction.from_bytes(raw_tx) # Correction pour la nouvelle version de la lib
            
            logger.info("Signing and sending transaction...")
            tx_signature = await self.async_client.send_transaction(transaction, self.payer)
            
            # 4. Confirm transaction
            await self.async_client.confirm_transaction(tx_signature.value)
            
            logger.success(f"Buy transaction confirmed! Signature: {tx_signature.value}")
            return str(tx_signature.value)


    async def _sell_on_jupiter(self, token_mint_address: str, amount_tokens: float) -> dict:
        """
        Vente réelle via Jupiter Aggregator (opérationnel).
        """
        if not self.payer:
            raise Exception("Payer keypair not loaded. Cannot execute real trade.")
        
        logger.info(f"Getting Jupiter quote for selling {amount_tokens} of {token_mint_address}")
        sol_mint = "So11111111111111111111111111111111111111112"
        amount_integer = int(amount_tokens) # Jupiter API expects an integer
        
        async with aiohttp.ClientSession() as session:
            # 1. Get quote
            quote_url = f'https://quote-api.jup.ag/v6/quote?inputMint={token_mint_address}&outputMint={sol_mint}&amount={amount_integer}&slippageBps=50'
            async with session.get(quote_url, timeout=10) as response:
                response.raise_for_status()
                quote_data = await response.json()                
                if 'error' in quote_data:
                    raise Exception(f"Jupiter quote API error: {quote_data.get('error', 'Unknown error')}")
            
            # 2. Get swap transaction
            logger.info("Getting swap transaction from Jupiter...")
            swap_payload = {
                "quoteResponse": quote_data,
                "userPublicKey": str(self.payer.public_key),
                "wrapAndUnwrapSol": True,
            }
            async with session.post('https://quote-api.jup.ag/v6/swap', json=swap_payload, timeout=10) as response:
                response.raise_for_status()
                swap_data = await response.json()
                swap_transaction = swap_data.get('swapTransaction')

            # 3. Sign and send transaction
            raw_tx = base64.b64decode(swap_transaction)
            transaction = Transaction.from_bytes(raw_tx) # Correction pour la nouvelle version de la lib
            
            logger.info("Signing and sending transaction...")
            tx_signature = await self.async_client.send_transaction(transaction, self.payer)
            
            # 4. Confirm transaction
            await self.async_client.confirm_transaction(tx_signature.value)
            
            logger.success(f"Sell transaction confirmed! Signature: {tx_signature.value}")            
            out_amount_sol = int(quote_data.get('outAmount', 0)) / 1e9
            return {"txid": str(tx_signature.value), "sell_price_sol": out_amount_sol}

    async def _buy_on_raydium(self, token_mint_address: str, amount_sol: float) -> str:
        """
        Achat réel via Raydium (SDK/API non intégré, fallback simulation).
        """
        logger.warning("Raydium non intégré, fallback simulation.")
        raise NotImplementedError("Intégration Raydium non implémentée.")

    async def _sell_on_raydium(self, token_mint_address: str, amount_tokens: float) -> str:
        """
        Vente réelle via Raydium (SDK/API non intégré, fallback simulation).
        """
        logger.warning("Raydium non intégré, fallback simulation.")
        raise NotImplementedError("Intégration Raydium non implémentée.")

    async def _buy_on_orca(self, token_mint_address: str, amount_sol: float) -> str:
        """
        Achat réel via Orca (SDK/API non intégré, fallback simulation).
        """
        logger.warning("Orca non intégré, fallback simulation.")
        raise NotImplementedError("Intégration Orca non implémentée.")

    async def _sell_on_orca(self, token_mint_address: str, amount_tokens: float) -> str:
        """
        Vente réelle via Orca (SDK/API non intégré, fallback simulation).
        """
        logger.warning("Orca non intégré, fallback simulation.")
        raise NotImplementedError("Intégration Orca non implémentée.")
