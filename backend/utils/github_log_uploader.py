import os
import requests
from loguru import logger

def upload_log_to_github(log_path, repo, branch="main", github_token=None):
    """
    Uploads a log file to a GitHub repository (private or public).
    Args:
        log_path: Path to the log file (str)
        repo: 'username/repo' (str)
        branch: Branch name (default 'main')
        github_token: Personal Access Token (str)
    """
    if github_token is None:
        github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GitHub token non trouvé dans .env ou argument.")
        return False
    if not os.path.exists(log_path):
        logger.error(f"Log file {log_path} not found.")
        return False
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    # GitHub API: create/update file
    api_url = f"https://api.github.com/repos/{repo}/contents/{os.path.basename(log_path)}"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    # Get SHA if file exists
    r = requests.get(api_url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    data = {
        "message": f"Update {os.path.basename(log_path)}",
        "content": content.encode("utf-8").decode("utf-8"),
        "branch": branch
    }
    if sha:
        data["sha"] = sha
    r = requests.put(api_url, headers=headers, json=data)
    if r.status_code in [200, 201]:
        logger.success(f"Log {log_path} uploaded to GitHub repo {repo}.")
        return True
    else:
        logger.error(f"GitHub upload failed: {r.text}")
        return False

if __name__ == "__main__":
    # Exemple d'utilisation
    repo = os.getenv("GITHUB_LOG_REPO", "username/repo")
    token = os.getenv("GITHUB_TOKEN")
    upload_log_to_github("simulation_trades.log", repo, github_token=token)
    upload_log_to_github("real_trades.log", repo, github_token=token)
