import os
import asyncio
import time
import sys, json, hashlib
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from dotenv import load_dotenv, set_key, dotenv_values
from typing import Optional, Dict, Any
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from collections import deque
# --- Import des modules du projet ---
from backend.ai_analysis.gemini_analyzer import GeminiAnalyzer
from backend.ai_analysis.ai_auto_optimizer import AIAutoOptimizer
from backend.trading.decision_module import DecisionModule
from backend.trading.order_executor import OrderExecutor
from backend.trading.new_pair_scanner import NewPairScanner  # Mis à jour avec le nouveau chemin
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
logger.add(os.path.join(LOGS_DIR, "backend.log"), rotation="10 MB", retention="7 days", level="INFO", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}")

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
        self.start_time: float = 0.0

    def setup_and_start(self, mode: str):
        if self.is_running:
            raise RuntimeError("Le bot est déjà en cours d'exécution.")

        logger.info(f"Configuration et démarrage du bot en mode '{mode}'...")
        self.current_mode = mode
        self.start_time = time.time()
        simulation = (mode == 'simulation')

        buy_amount_sol = float(os.getenv("BUY_AMOUNT_SOL", "0.01"))
        sell_multiplier = float(os.getenv("SELL_MULTIPLIER", "2.0"))
        trailing_stop_percent = float(os.getenv("TRAILING_STOP_PERCENT", "0.15"))

        self.order_executor = OrderExecutor(settings.SOLANA_RPC_URL, settings.PRIVATE_KEY, simulate=simulation)
        self.decision_module = DecisionModule(self, self.order_executor, buy_amount_sol, sell_multiplier, trailing_stop_percent, simulation_mode=simulation)
        self.pair_scanner = NewPairScanner(websocket_url=settings.SOLANA_WS_URL, decision_module=self.decision_module)

        # L'optimiseur IA n'est actif qu'en mode simulation pour analyser et ajuster les stratégies.
        if simulation:
            self.ai_optimizer = AIAutoOptimizer(self.decision_module)
            gemini_api_keys = [
                os.getenv("GEMINI_API_KEY_1"),
                os.getenv("GEMINI_API_KEY_2"),
                os.getenv("GEMINI_API_KEY_3"),
            ]
            
            gemini_analyzer = GeminiAnalyzer(api_keys=gemini_api_keys)
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
        status = {
            "is_running": self.is_running,
            "current_mode": self.current_mode or "stopped",
            "is_offline": False,
            "uptime": time.time() - self.start_time if self.is_running else 0,
            "active_trades": len(self.decision_module.held_tokens) if self.decision_module else 0,
            "last_scan": time.time(),  # Timestamp du dernier scan
            "trades_24h": 0,  # À implémenter : nombre de trades des dernières 24h
            "success_rate": 0.0  # À implémenter : taux de réussite
        }
        return status

    def log_activity(self, message: str, level: str = "INFO"):
        """Enregistre une activité pour l'afficher dans le dashboard."""
        if not hasattr(self, 'activity_log'):
            # Utiliser une deque pour une performance optimale et une taille limitée
            self.activity_log = deque(maxlen=100)
        
        log_entry = {
            "timestamp": time.time(),
            "message": message,
            "level": level.upper()
        }
        self.activity_log.appendleft(log_entry) # Ajouter au début
        logger.info(f"[Activity] {message}")

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
import glob

@app.get("/")
async def read_root():
    """Endpoint racine pour vérifier que l'API est en ligne."""
    return {"message": "Welcome to AlphaStriker API"}

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

@app.get("/api/bot/activity")
async def get_bot_activity():
    """Renvoie le journal d'activité récent du bot."""
    # Retourne une liste vide si le bot n'est pas en cours d'exécution ou si aucun log n'est disponible.
    # C'est plus propre pour l'interface qui s'attend à un tableau.
    return list(getattr(app.state.bot_manager, 'activity_log', []))

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

# --- API pour l'historique des trades réels ---
@app.get("/api/real/dashboard")
def real_dashboard():
    """Retourne l'historique des trades réels pour affichage dans le dashboard."""
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    LOGS_DIR = os.path.join(ROOT_DIR, "logs")
    log_file = os.path.join(LOGS_DIR, "real_trades.log")
    trade_history = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    trade_history.append(json.loads(line.strip()))
                except Exception:
                    continue
    return {
        "total_trades": len(trade_history),
        "trade_history": trade_history
    }

@app.get("/api/ai/status")
def get_ai_status():
    """Retourne l'état complet du module d'optimisation IA."""
    bot_manager = app.state.bot_manager
    if not bot_manager.ai_optimizer:
        return {"is_running": False}
    
    return bot_manager.ai_optimizer.get_status_dict()


@app.get("/api/bot/readiness")
async def get_real_mode_readiness():
    """Vérifie si le bot est prêt pour le mode réel (clés, solde, etc.)."""
    checks = {
        "private_key_set": False,
        "wallet_address_set": False,
        "helius_key_set": False, # Helius est recommandé pour la performance
        "initial_balance_ok": False,
        "balance_sol": 0.0,
        "error": None
    }
    missing_items = []

    private_key = os.getenv("PRIVATE_KEY")
    if private_key:
        checks["private_key_set"] = True
    else:
        missing_items.append("Clé privée (PRIVATE_KEY) manquante")

    if os.getenv("WALLET_ADDRESS"):
        checks["wallet_address_set"] = True
    else:
        missing_items.append("Adresse de wallet (WALLET_ADDRESS) manquante")

    if os.getenv("HELIUS_API_KEY"):
        checks["helius_key_set"] = True

    if private_key:
        try:
            temp_executor = OrderExecutor(settings.SOLANA_RPC_URL, private_key, simulate=False)
            wallet_status = await temp_executor.get_wallet_status()
            checks["balance_sol"] = wallet_status.get("balance_sol", 0)
            buy_amount = float(os.getenv("BUY_AMOUNT_SOL", "0.01"))
            if checks["balance_sol"] >= buy_amount:
                checks["initial_balance_ok"] = True
            else:
                missing_items.append(f"Solde insuffisant (actuel: {checks['balance_sol']:.4f} SOL, requis: {buy_amount} SOL)")
        except Exception as e:
            checks["error"] = f"Erreur de validation de la clé privée ou de connexion RPC: {e}"
            missing_items.append("Clé privée invalide ou problème RPC")

    is_ready = all([checks["private_key_set"], checks["initial_balance_ok"]])
    return {"is_ready": is_ready, "checks": checks, "missing_items": missing_items}

# --- API de Configuration ---
@app.get("/api/env")
def get_env_variables():
    """Retourne les variables d'environnement non sensibles pour l'UI."""
    env_values = dotenv_values(os.path.join(ROOT_DIR, ".env"))
    safe_values = {
        "BUY_AMOUNT_SOL": env_values.get("BUY_AMOUNT_SOL"),
        "SELL_MULTIPLIER": env_values.get("SELL_MULTIPLIER"),
        "TRAILING_STOP_PERCENT": env_values.get("TRAILING_STOP_PERCENT"),
        "GEMINI_MODEL": env_values.get("GEMINI_MODEL"),
        "GEMINI_API_KEY_1": env_values.get("GEMINI_API_KEY_1"),
        "GEMINI_API_KEY_2": env_values.get("GEMINI_API_KEY_2"),
        "GEMINI_API_KEY_3": env_values.get("GEMINI_API_KEY_3"),
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
        "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_MODEL"
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
                if 'GEMINI_API_KEY' in key:
                    # Recharger les variables d'environnement pour que os.getenv voie les nouvelles valeurs
                    load_dotenv(override=True)
                    # Recharger toutes les clés
                    new_keys = [
                        os.getenv("GEMINI_API_KEY_1"),
                        os.getenv("GEMINI_API_KEY_2"),
                        os.getenv("GEMINI_API_KEY_3"),
                    ]                    
                    bot_manager.ai_optimizer.gemini_analyzer.update_api_keys(new_keys)
                elif key == 'GEMINI_MODEL':
                    bot_manager.ai_optimizer.gemini_analyzer.update_model(value)

        return {"status": "ok", "key": key, "value": value}
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier .env : {e}")
        raise HTTPException(status_code=500, detail=str(e))