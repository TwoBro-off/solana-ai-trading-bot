import os
import subprocess
import datetime
import logging

def github_auto_backup():
    repo_url = os.getenv("GITHUB_REPO_URL")
    github_token = os.getenv("GITHUB_TOKEN")
    if not repo_url or not github_token:
        logging.error("GITHUB_REPO_URL ou GITHUB_TOKEN manquant dans .env")
        return False
    branch = "backup-auto"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    commit_msg = f"[AUTO-BACKUP] Backup automatique {now}"
    # Configure remote avec token
    remote_url = repo_url.replace("https://", f"https://{github_token}@")
    try:
        subprocess.run(["git", "checkout", "-B", branch], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=False)
        subprocess.run(["git", "push", remote_url, branch, "--force"], check=True)
        logging.info(f"Backup auto GitHub effectué sur {branch} à {now}")
        return True
    except Exception as e:
        logging.error(f"Erreur backup auto GitHub : {e}")
        return False

if __name__ == "__main__":
    github_auto_backup()
