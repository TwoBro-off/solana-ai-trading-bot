import os
import json
import asyncio
from loguru import logger
from typing import Optional, Any, Dict, List

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


class GeminiAnalyzer:
    """Operational Gemini/OpenRouter analyzer.
    
    Features:
    - Uses aiohttp to call the Google Gemini API.
    - Manages a pool of API keys and rotates them if a quota error is detected.
    - Retries with exponential backoff on transient errors.
    - Timeouts for network calls.
    - Local fallback summary when no API key is configured.
    """

    def __init__(
        self,
        api_keys: List[str],
        model: Optional[str] = None,
        timeout: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.api_keys = [key for key in api_keys if key]
        self.current_key_index = 0
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        logger.info(
            f"GeminiAnalyzer initialized (model={self.model}, num_keys={len(self.api_keys)})"
        )

    def _get_current_api_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_index]

    def _rotate_api_key(self):
        if not self.api_keys:
            return
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.warning(f"Switching to Gemini API Key #{self.current_key_index + 1} due to potential quota issues.")

    async def analyze_logs(self, log_path: str) -> Dict[str, Any]:
        """Analyze a JSON-lines trade log and either call the model or perform a local summary.

        Returns a dict with keys like 'summary', 'suggestions', 'raw_response' (when available).
        """
        logger.info(f"Starting analysis for {log_path}")
        trades = self._read_trades(log_path)
        if trades is None:
            return {"error": "log_not_found", "path": log_path}

        # If no API key is configured, return a local quick summary to avoid blocking
        if not self._get_current_api_key():
            logger.warning("No GEMINI_API_KEY set — returning local summary fallback.")
            return {"mode": "local_summary", "result": self._local_summary(trades)}

        try:
            response = await self._call_model(trades)
            return response
        except Exception as e:
            logger.exception(f"Remote analysis failed: {e}")
            # Fallback to local summary when remote call fails
            return {"mode": "fallback_local", "error": str(e), "result": self._local_summary(trades)}

    def update_api_keys(self, keys: List[str]):
        self.api_keys = [key for key in keys if key]
        self.current_key_index = 0
        logger.info(f"GEMINI_API_KEYs updated. Found {len(self.api_keys)} keys.")

    def update_model(self, model: str):
        self.model = model
        logger.info(f"GEMINI_MODEL updated -> {self.model}")

    def _read_trades(self, log_path: str) -> Optional[List[Dict[str, Any]]]:
        if not os.path.exists(log_path):
            return None
        trades: List[Dict[str, Any]] = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trades.append(json.loads(line))
                    except Exception:
                        # ignore malformed lines
                        continue
        except Exception:
            return None
        # Keep last 1000 trades to limit prompt size
        return trades[-1000:]

    def _local_summary(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        wins = 0
        losses = 0
        profit = 0.0
        buy_prices: Dict[str, float] = {}
        total = 0
        for entry in trades:
            total += 1
            action = entry.get("action")
            token = entry.get("token")
            price = float(entry.get("price", 0) or 0)
            if action == "buy" and token:
                buy_prices[token] = price
            elif action == "sell" and token and token in buy_prices:
                p = price - buy_prices[token]
                profit += p
                if p > 0:
                    wins += 1
                else:
                    losses += 1

        return {"total_trades": total, "wins": wins, "losses": losses, "net_profit": profit}

    async def _call_model(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        import aiohttp

        # Build a compact textual summary as the user message
        sample = json.dumps(trades[-200:], ensure_ascii=False)
        system_prompt = (
            "You are an expert trading assistant. Analyze the provided trade events (JSON list) "
            "and return a concise JSON object with: summary (one paragraph), winrate, net_profit, potential_issues, actionable_suggestions. "
            "Return ONLY valid JSON in the assistant reply."
        )
        user_prompt = f"Analyze these trades: {sample}"

        payload = {
            "contents": [{"parts": [{"text": system_prompt}, {"text": user_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }

        headers = {"Content-Type": "application/json"}

        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= self.max_retries:
            attempt += 1
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                api_key = self._get_current_api_key()
                if not api_key:
                    raise RuntimeError("No API Key available.")
                
                url_with_key = f"{self.endpoint}?key={api_key}"

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url_with_key, json=payload, headers=headers) as resp:
                        text = await resp.text()

                        # Handle quota errors by rotating key
                        if resp.status == 429:
                            self._rotate_api_key()
                            raise RuntimeError(f"Rate limited (429): {text}")

                        if resp.status >= 500:
                            raise RuntimeError(f"Server error {resp.status}: {text}")
                        if resp.status >= 400:
                            return {"mode": "remote_error", "status": resp.status, "body": text}

                        try:
                            data = json.loads(text)
                        except Exception:
                            raise ValueError(f"Failed to parse JSON response: {text}")

                        # Extract content from Gemini's response structure
                        content_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                        parsed = None
                        if content_text:
                            try:
                                parsed = json.loads(content_text)
                            except Exception:
                                parsed = {"text": content_text}
                        
                        result = {"mode": "remote", "status": resp.status, "raw_response": data, "parsed": parsed}
                        logger.info(f"Remote analysis successful (attempt {attempt})")
                        return result
            except Exception as e:
                last_exc = e
                wait = self.backoff_factor * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

        raise RuntimeError(f"All retries failed: {last_exc}")
