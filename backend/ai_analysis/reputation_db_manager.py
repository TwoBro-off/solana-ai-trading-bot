from sqlalchemy.orm import Session
from loguru import logger
from ..database.db import DatabaseManager, ReputationEntry

class ReputationDBManager:
    def __init__(self, database_url: str):
        self.db_manager = DatabaseManager(database_url)

    async def connect(self):
        await self.db_manager.connect()
        logger.info("Reputation database connected.")

    async def disconnect(self):
        await self.db_manager.disconnect()

    def add_entry(self, wallet_id: str, ip_publique: str = None, tags: str = None, comportement: str = None, score_de_confiance: float = 0.5):
        with self.db_manager.SessionLocal() as db:
            existing_entry = db.query(ReputationEntry).filter(ReputationEntry.wallet_id == wallet_id).first()
            if existing_entry:
                existing_entry.ip_publique = ip_publique if ip_publique is not None else existing_entry.ip_publique
                existing_entry.tags = tags if tags is not None else existing_entry.tags
                existing_entry.comportement = comportement if comportement is not None else existing_entry.comportement
                existing_entry.score_de_confiance = score_de_confiance
            else:
                new_entry = ReputationEntry(
                    wallet_id=wallet_id,
                    ip_publique=ip_publique,
                    tags=tags,
                    comportement=comportement,
                    score_de_confiance=score_de_confiance
                )
                db.add(new_entry)
            db.commit()

    def get_entry(self, wallet_id: str) -> ReputationEntry:
        with self.db_manager.SessionLocal() as db:
            return db.query(ReputationEntry).filter(ReputationEntry.wallet_id == wallet_id).first()

    def get_all_entries(self):
        with self.db_manager.SessionLocal() as db:
            entries = db.query(ReputationEntry).all()
            return [{
                "wallet_id": entry.wallet_id,
                "ip_publique": entry.ip_publique,
                "tags": entry.tags,
                "comportement": entry.comportement,
                "score_de_confiance": entry.score_de_confiance
            } for entry in entries]