import os
import asyncio
import sys, json, hashlib
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from dotenv import load_dotenv, set_key, dotenv_values
from typing import Optional, Dict, Any
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- Import des modules du projet ---
from backend.ai_analysis.gemini_analyzer import GeminiAnalyzer
from backend.ai_analysis.ai_auto_optimizer import AIAutoOptimizer
from backend.trading.decision_module import DecisionModule
from backend.new_pair_scanner import NewPairScanner
from backend.config.settings import settings

# ==============================================================================
# Configuration Initiale
# ==============================================================================

load_dotenv()

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logger.remove()
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", level="INFO")
logger.add(os.path.join(LOGS_DIR, "backend.log"), rotation="10 MB", retention="7 days", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}")

app = FastAPI(title="AlphaStriker API")

# --- Configuration CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Gestionnaire de Cycle de Vie du Bot ---
class BotManager:
    """Classe centrale qui gère l'état et les composants du bot."""
    def __init__(self):
        self.order_executor: Optional[OrderExecutor] = None
        self.decision_module: Optional[DecisionModule] = None
        self.pair_scanner: Optional[NewPairScanner] = None
        self.ai_optimizer: Optional[AIAutoOptimizer] = None
        self.is_running = False
        self.current_mode: Optional[str] = None

    def setup_and_start(self, mode: str):
        if self.is_running:
            raise RuntimeError("Le bot est déjà en cours d'exécution.")

        logger.info(f"Configuration et démarrage du bot en mode '{mode}'...")
        self.current_mode = mode
        simulation = (mode == 'simulation')

        buy_amount_sol = float(os.getenv("BUY_AMOUNT_SOL", "0.01"))
        sell_multiplier = float(os.getenv("SELL_MULTIPLIER", "2.0"))
        trailing_stop_percent = float(os.getenv("TRAILING_STOP_PERCENT", "0.15"))

        self.order_executor = OrderExecutor(settings.SOLANA_RPC_URL, settings.PRIVATE_KEY, simulate=simulation)
        self.decision_module = DecisionModule(self.order_executor, buy_amount_sol, sell_multiplier, trailing_stop_percent, simulation_mode=simulation)
        self.pair_scanner = NewPairScanner(websocket_url=settings.SOLANA_WSS_URL, decision_module=self.decision_module)

        # L'optimiseur IA n'est actif qu'en mode simulation pour analyser et ajuster les stratégies.
        if simulation:
            self.ai_optimizer = AIAutoOptimizer(self.decision_module)
            gemini_analyzer = GeminiAnalyzer(api_key=os.getenv("OPENROUTER_API_KEY"))
            self.ai_optimizer.set_gemini_analyzer(gemini_analyzer)
            self.ai_optimizer.start() # Start AI optimizer thread

        # Démarrer le scanner de nouvelles paires Raydium en tâche de fond
        asyncio.create_task(self.pair_scanner.start())

        self.is_running = True
        logger.success(f"Bot démarré avec succès en mode {mode}.")

    def stop(self):
        logger.info("Arrêt des services du bot...")
        if self.pair_scanner: # La méthode stop est maintenant synchrone
            self.pair_scanner.stop()
        if self.ai_optimizer:
            self.ai_optimizer.stop()

        self.is_running = False
        self.current_mode = None
        logger.success("Tous les services du bot ont été arrêtés.")

    def get_status(self):
        return {"is_running": self.is_running, "current_mode": self.current_mode}

# ==============================================================================
# Événements de Cycle de Vie de l'Application
# ==============================================================================

@app.on_event("startup")
async def startup_event():
    """Crée l'instance du BotManager au démarrage de l'application."""
    app.state.bot_manager = BotManager()
    logger.info("Backend démarré. BotManager initialisé. En attente des commandes.")

@app.on_event("shutdown")
def shutdown_event():
    """Arrête proprement le bot lors de l'arrêt de l'application."""
    if hasattr(app.state, 'bot_manager'):
        app.state.bot_manager.stop()
    logger.info("Backend arrêté.")

# ==============================================================================
# Endpoints de l'API
# ==============================================================================

# --- API de Contrôle du Bot ---
@app.post("/api/bot/start")
async def start_bot(mode: str = Query(..., description="Le mode: 'simulation' ou 'real'")):
    try:
        app.state.bot_manager.setup_and_start(mode)
        return {"status": f"Bot en cours de démarrage en mode {mode}..."}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/bot/stop")
async def stop_bot():
    app.state.bot_manager.stop()
    return {"status": "Bot arrêté."}

@app.get("/api/bot/status")
async def get_bot_status():
    return app.state.bot_manager.get_status()

# --- API de Données et de Statut ---
@app.get("/api/dashboard")
def dashboard():
    bot_manager = app.state.bot_manager
    ai_optimizer = bot_manager.ai_optimizer

    return {
        "status": "running",
        "bot_status": bot_manager.get_status(),
        "ai_optimizer_status": ai_optimizer.get_status_dict() if ai_optimizer else None
    }

@app.get("/api/simulation/dashboard")
def simulation_dashboard():
    bot_manager = app.state.bot_manager
    if not bot_manager.is_running or not bot_manager.decision_module:
        return {"profit_loss_sol": 0, "total_trades": 0, "held_tokens_count": 0, "trade_history": []}
    
    if not bot_manager.decision_module.simulation_mode:
        raise HTTPException(status_code=400, detail="Le bot n'est pas en mode simulation.")
    
    return {
        "profit_loss_sol": bot_manager.decision_module.get_simulation_profit_loss(),
        "total_trades": len(bot_manager.decision_module.simulation_results),
        "held_tokens_count": len(bot_manager.decision_module.held_tokens),
        "trade_history": bot_manager.decision_module.simulation_results
    }

# --- API de Configuration ---
@app.get("/api/env")
def get_env_variables():
    """Retourne les variables d'environnement non sensibles pour l'UI."""
    env_values = dotenv_values(os.path.join(ROOT_DIR, ".env"))
    safe_values = {
        "BUY_AMOUNT_SOL": env_values.get("BUY_AMOUNT_SOL"),
        "SELL_MULTIPLIER": env_values.get("SELL_MULTIPLIER"),
        "TRAILING_STOP_PERCENT": env_values.get("TRAILING_STOP_PERCENT"),
        "OPENROUTER_MODEL": env_values.get("OPENROUTER_MODEL"),
    }
    return safe_values

@app.post("/api/env/update")
async def update_env_variable(data: Dict[str, str]):
    """Met à jour une variable d'environnement dans le fichier .env."""
    key = data.get("key")
    value = data.get("value")
    if not key or value is None:
        raise HTTPException(status_code=400, detail="Clé ou valeur manquante.")

    # Liste des clés autorisées à être modifiées pour la sécurité
    allowed_keys = [
        "BUY_AMOUNT_SOL", "SELL_MULTIPLIER", "TRAILING_STOP_PERCENT",
        "OPENROUTER_API_KEY", "OPENROUTER_MODEL"
    ]
    if key not in allowed_keys:
        raise HTTPException(status_code=403, detail=f"La modification de la clé '{key}' n'est pas autorisée.")
    
    env_path = os.path.join(ROOT_DIR, ".env")
    try:
        set_key(env_path, key, value)

        # Mettre à jour dynamiquement les modules en cours d'exécution
        if app.state.bot_manager.is_running:
            bot_manager = app.state.bot_manager
            if bot_manager.decision_module:
                if key == 'BUY_AMOUNT_SOL':
                    bot_manager.decision_module.set_param('buy_amount_sol', float(value))
                elif key == 'SELL_MULTIPLIER':
                    bot_manager.decision_module.set_param('sell_multiplier', float(value))
                elif key == 'TRAILING_STOP_PERCENT':
                    bot_manager.decision_module.set_param('trailing_stop_percent', float(value))
            
            if bot_manager.ai_optimizer and bot_manager.ai_optimizer.gemini_analyzer:
                if key == 'OPENROUTER_API_KEY':
                    bot_manager.ai_optimizer.gemini_analyzer.update_api_key(value)
                elif key == 'OPENROUTER_MODEL':
                    bot_manager.ai_optimizer.gemini_analyzer.update_model(value)

        return {"status": "ok", "key": key, "value": value}
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier .env : {e}")
        raise HTTPException(status_code=500, detail=str(e))