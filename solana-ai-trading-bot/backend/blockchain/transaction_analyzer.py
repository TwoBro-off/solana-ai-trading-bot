import asyncio
from loguru import logger
from ..database.db import DatabaseManager, Transaction, Alert
from .rpc_client import call_solana_rpc

class TransactionAnalyzer:
    def __init__(self, database_url: str, rpc_url: str):
        self.db_manager = DatabaseManager(database_url)
        self.rpc_url = rpc_url

    async def analyze_token_transactions(self, mint_address: str):
        logger.info(f"Analyse des transactions pour le token {mint_address}")
        # Récupérer les transactions du token (exemple simplifié : recherche sur le mint)
        resp = await call_solana_rpc(self.rpc_url, "getSignaturesForAddress", [mint_address, {"limit": 100}])
        if not resp or not resp.get("result"):
            logger.warning(f"Aucune transaction trouvée pour le token {mint_address}")
            return
        signatures = [tx['signature'] for tx in resp['result']]
        for signature in signatures:
            tx_resp = await call_solana_rpc(self.rpc_url, "getTransaction", [signature, {"encoding": "json"}])
            if not tx_resp or not tx_resp.get("result"):
                continue
            tx = tx_resp["result"]
            # Parcourir les instructions pour détecter des achats sur DEX (exemple : Raydium, Orca, Jupiter, Pump.fun)
            for instr in tx["transaction"]["message"]["instructions"]:
                program_id = instr.get("programId")
                # Liste des Program ID connus pour les DEX Solana (à compléter)
                dex_programs = [
                    "4ckmDgGzLYLyF6jQKqQy1e1p9n3x3bYvY2d5n5wFhS5E", # Raydium
                    "9WwGQq5pKk5k5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q", # Orca (exemple)
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", # SPL Token (pour transferts directs)
                    # Ajouter d'autres DEX ici
                ]
                if program_id in dex_programs:
                    accounts = instr.get("accounts", [])
                    if len(accounts) >= 2:
                        source = tx["transaction"]["message"]["accountKeys"][accounts[0]]
                        dest = tx["transaction"]["message"]["accountKeys"][accounts[1]]
                        logger.info(f"Achat détecté : {source} -> {dest} sur {program_id}")
                        # Enregistrer la transaction si ce n'est pas déjà fait
                        with self.db_manager.SessionLocal() as db:
                            db_tx = db.query(Transaction).filter_by(signature=signature).first()
                            if not db_tx:
                                db_tx = Transaction(signature=signature, slot=tx.get("slot"), source=source, destination=dest, amount=0, token_mint=mint_address)
                                db.add(db_tx)
                                db.commit()
                        # Préparer la détection de comportements suspects (à implémenter)
                        # await self.detect_suspicious_behavior(source, dest, mint_address) 