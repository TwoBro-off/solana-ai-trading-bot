import os
import subprocess
import logging
import shutil
import datetime

BACKUP_DIR = "auto_update_backups"
REPO_URL = os.getenv("GITHUB_REPO_URL")
BRANCH = os.getenv("AUTO_UPDATE_BRANCH", "main")


def backup_current_code():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns(BACKUP_DIR, ".git", "__pycache__", "*.db", "node_modules", "*.log"))
    return backup_path


def restore_backup(backup_path):
    for item in os.listdir(backup_path):
        s = os.path.join(backup_path, item)
        d = os.path.join(".", item)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


def auto_update():
    logging.info("[AUTO-UPDATE] Démarrage de la mise à jour automatique...")
    backup_path = backup_current_code()
    try:
        subprocess.run(["git", "fetch", "origin", BRANCH], check=True)
        subprocess.run(["git", "reset", "--hard", f"origin/{BRANCH}"], check=True)
        logging.info("[AUTO-UPDATE] Mise à jour réussie depuis la branche %s", BRANCH)
        return True, backup_path
    except Exception as e:
        logging.error(f"[AUTO-UPDATE] Erreur lors de la mise à jour : {e}. Restauration du backup...")
        restore_backup(backup_path)
        return False, backup_path

if __name__ == "__main__":
    ok, backup = auto_update()
    if ok:
        print(f"Mise à jour réussie. Backup : {backup}")
    else:
        print(f"Échec de la mise à jour. Restauration effectuée depuis : {backup}")
