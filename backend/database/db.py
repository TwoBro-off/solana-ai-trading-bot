from sqlalchemy import create_engine, Column, String, Float, Text, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

Base = declarative_base()

class ReputationEntry(Base):
    __tablename__ = "reputation_entries"

    wallet_id = Column(String, primary_key=True, index=True)
    ip_publique = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    comportement = Column(Text, nullable=True)
    score_de_confiance = Column(Float, default=0.5)

    def __repr__(self):
        return f"<ReputationEntry(wallet_id='{self.wallet_id}', score={self.score_de_confiance})>"

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mint_address = Column(String, unique=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False) # Assure un lien obligatoire
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    creator = relationship("Creator", back_populates="tokens") # La relation existe déjà, c'est parfait

class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, unique=True, index=True)
    tokens = relationship("Token", back_populates="creator")
    linked_accounts = relationship("LinkedAccount", back_populates="creator")

class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String, unique=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"))
    creator = relationship("Creator", back_populates="linked_accounts")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signature = Column(String, unique=True, index=True)
    slot = Column(Integer)
    source = Column(String, index=True)
    destination = Column(String, index=True)
    amount = Column(Float)
    token_mint = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_mint = Column(String, index=True)
    creator_address = Column(String, index=True)
    linked_account = Column(String, index=True)
    alert_type = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    async def connect(self):
        Base.metadata.create_all(bind=self.engine)

    async def disconnect(self):
        pass

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()