import networkx as nx
from loguru import logger
from ..database.db import DatabaseManager, LinkedAccount, Creator, Transaction, Alert

class LinkedAccountDetector:
    def __init__(self, database_url: str):
        self.db_manager = DatabaseManager(database_url)

    def detect_clusters(self, creator_address: str):
        logger.info(f"Détection de clusters d'adresses liés à {creator_address}")
        G = nx.DiGraph()
        with self.db_manager.SessionLocal() as db:
            # Ajouter les transactions du créateur et des comptes liés
            creator = db.query(Creator).filter_by(address=creator_address).first()
            if not creator:
                return []
            linked_accounts = db.query(LinkedAccount).filter_by(creator_id=creator.id).all()
            addresses = [creator_address] + [acc.address for acc in linked_accounts]
            txs = db.query(Transaction).filter(Transaction.source.in_(addresses)).all()
            for tx in txs:
                G.add_edge(tx.source, tx.destination)
        # Détecter les clusters (composantes fortement connexes)
        clusters = list(nx.strongly_connected_components(G))
        logger.info(f"Clusters détectés : {clusters}")
        return clusters

    def detect_suspicious_behavior(self, creator_address: str, mint_address: str):
        clusters = self.detect_clusters(creator_address)
        # Critère simple : si un cluster contient le créateur ET un compte qui a acheté le token, alerter
        with self.db_manager.SessionLocal() as db:
            for cluster in clusters:
                if creator_address in cluster:
                    # Chercher si un membre du cluster a acheté le token
                    txs = db.query(Transaction).filter(Transaction.source.in_(cluster), Transaction.token_mint == mint_address).all()
                    for tx in txs:
                        if tx.source != creator_address:
                            logger.warning(f"Comportement suspect : {tx.source} (lié au créateur) a acheté le token {mint_address}")
                            # Générer une alerte
                            alert = Alert(token_mint=mint_address, creator_address=creator_address, linked_account=tx.source, alert_type="self-buy", description="Achat suspect du token par un compte lié au créateur.")
                            db.add(alert)
                            db.commit() 