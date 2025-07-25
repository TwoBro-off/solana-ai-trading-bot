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
    MIN_LIQUIDITY_POOL_SOL = float(os.getenv("MIN_LIQUIDITY_POOL_SOL", 3.0))
    BUY_AMOUNT_SOL = float(os.getenv("BUY_AMOUNT_SOL", 0.01))
    SELL_MULTIPLIER = float(os.getenv("SELL_MULTIPLIER", 2.0))
    REPUTATION_SCORE_THRESHOLD = float(os.getenv("REPUTATION_SCORE_THRESHOLD", 0.7))
    RPC_LATENCY_CHECK_INTERVAL = int(os.getenv("RPC_LATENCY_CHECK_INTERVAL", 5))
    TOKEN_SCAN_INTERVAL = int(os.getenv("TOKEN_SCAN_INTERVAL", 2))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s %(levelname)s %(message)s")
    PROFIT_MULTIPLIER_SELL = float(os.getenv("PROFIT_MULTIPLIER_SELL", 2.0)) # Vente si profit >= x2
    STOP_LOSS_PROFIT_MULTIPLIER = float(os.getenv("STOP_LOSS_PROFIT_MULTIPLIER", 5.0)) # Stop loss dynamique si profit atteint x5

    # Latency Monitoring
    LATENCY_TARGET_MS = int(os.getenv("LATENCY_TARGET_MS", 150))

    # AI Analysis (Gemini)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "google/gemini-flash-1.5")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./solana_bot.db")

    # Simulation Mode
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "False").lower() == "true"
    SIMULATION_REPORT_PATH = os.getenv("SIMULATION_REPORT_PATH", "simulation_report.csv")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
