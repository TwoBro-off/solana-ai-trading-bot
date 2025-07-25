import asyncio
from loguru import logger
from ..database.db import DatabaseManager, LinkedAccount, Creator, Transaction
from .rpc_client import call_solana_rpc

class CreatorTracker:
    def __init__(self, database_url: str, rpc_url: str):
        self.db_manager = DatabaseManager(database_url)
        self.rpc_url = rpc_url

    async def track(self, creator_address: str, mint_address: str):
        logger.info(f"Tracking les transactions du créateur {creator_address} pour le token {mint_address}")
        # Récupérer les signatures de transactions du créateur
        resp = await call_solana_rpc(self.rpc_url, "getSignaturesForAddress", [creator_address, {"limit": 100}])
        if not resp or not resp.get("result"):
            logger.warning(f"Aucune transaction trouvée pour {creator_address}")
            return
        signatures = [tx['signature'] for tx in resp['result']]
        linked_accounts = set()
        for signature in signatures:
            tx_resp = await call_solana_rpc(self.rpc_url, "getTransaction", [signature, {"encoding": "json"}])
            if not tx_resp or not tx_resp.get("result"):
                continue
            tx = tx_resp["result"]
            # Parcourir les instructions pour détecter des transferts
            for instr in tx["transaction"]["message"]["instructions"]:
                if instr.get("programId") == "11111111111111111111111111111111":  # System Program (transfert SOL)
                    accounts = instr.get("accounts", [])
                    if len(accounts) >= 2:
                        source = tx["transaction"]["message"]["accountKeys"][accounts[0]]
                        dest = tx["transaction"]["message"]["accountKeys"][accounts[1]]
                        if source == creator_address and dest != creator_address:
                            linked_accounts.add(dest)
                            logger.info(f"Transfert détecté du créateur {creator_address} vers {dest}")
                            # Enregistrer dans LinkedAccount
                            with self.db_manager.SessionLocal() as db:
                                creator = db.query(Creator).filter_by(address=creator_address).first()
                                if creator:
                                    linked = db.query(LinkedAccount).filter_by(address=dest).first()
                                    if not linked:
                                        linked = LinkedAccount(address=dest, creator_id=creator.id)
                                        db.add(linked)
                                        db.commit()
            # Enregistrer la transaction
            with self.db_manager.SessionLocal() as db:
                for instr in tx["transaction"]["message"]["instructions"]:
                    accounts = instr.get("accounts", [])
                    if len(accounts) >= 2:
                        source = tx["transaction"]["message"]["accountKeys"][accounts[0]]
                        dest = tx["transaction"]["message"]["accountKeys"][accounts[1]]
                        db_tx = db.query(Transaction).filter_by(signature=signature).first()
                        if not db_tx:
                            db_tx = Transaction(signature=signature, slot=tx.get("slot"), source=source, destination=dest, amount=0, token_mint=mint_address)
                            db.add(db_tx)
                            db.commit()
        logger.info(f"Comptes liés trouvés pour {creator_address}: {linked_accounts}") 