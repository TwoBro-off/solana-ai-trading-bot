import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Solana RPC
    SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.mainnet-beta.solana.com/")
    JITO_SHREDSTREAM_GRPC_URL = os.getenv("JITO_SHREDSTREAM_GRPC_URL", "frankfurt.mainnet.jito.wtf:8001")
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")

    # Wallet (à renseigner par l'utilisateur)
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")

    # Trading Parameters
    INITIAL_CAPITAL_SOL = float(os.getenv("INITIAL_CAPITAL_SOL", 0.05)) # 10€ par défaut

    # AI Analysis (Gemini)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./solana_bot.db")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
