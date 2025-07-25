"""
Fichier agent autonome pour Gemini (OpenRouter)
Ce module reste fonctionnel même si le reste du projet est cassé (sauf main.py et requirements.txt).
Il permet à Gemini de :
- Lire, modifier, créer des fichiers du projet
- Réparer automatiquement le code ou restaurer des fichiers critiques
- Exécuter des diagnostics et proposer des correctifs
- Piloter le bot en mode dégradé
"""
import os
import sys
from loguru import logger

class GeminiAgent:
    def __init__(self, root_dir="."):
        self.root_dir = root_dir

    def list_files(self):
        """Liste tous les fichiers du projet (hors dossiers cachés et node_modules/venv)."""
        files = []
        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("node_modules", "venv", "__pycache__")]
            for f in filenames:
                if not f.startswith('.'):
                    files.append(os.path.join(root, f))
        return files

    def read_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[Erreur lecture: {e}]"

    def write_file(self, path, content):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Erreur écriture {path}: {e}")
            return False

    def repair_project(self):
        """Exemple: restaure main.py ou requirements.txt si manquants."""
        # ... logique de réparation automatique ...
        pass

    def run_diagnostics(self):
        """Exécute des diagnostics sur le projet et propose des correctifs."""
        # ... logique de diagnostic ...
        pass

# Ce fichier doit toujours rester fonctionnel et non supprimé.
