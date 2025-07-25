#!/bin/bash

# Script d'installation automatisée du bot Solana AI Trading
# Usage : bash install_bot.sh

echo "Installation du bot Solana AI Trading..."

# 1. Mise à jour système & dépendances
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git ufw

# 2. Création de l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installation des dépendances Python
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Configuration du firewall pour le dashboard (port 8000 et 3000)
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp

# 5. Création du fichier .env interactif
cat <<EOF > .env
WEB_USERNAME=admin
WEB_PASSWORD=$(openssl rand -hex 8)
GEMINI_API_KEY=
TRUSTWALLET_ADDRESS=
RPC_URL=https://api.mainnet-beta.solana.com
INITIAL_CAPITAL_SOL=0.05
MODE=simulation
EOF

echo "Fichier .env généré. Renseigne ta clé Gemini et ton adresse TrustWallet dans .env !"

# 6. Lancement du backend
nohup venv/bin/python backend/main.py &

# 7. Lancement du frontend (React)
cd frontend
npm install
npm run build
npm run start &

cd ..

echo "Bot lancé ! Accède à l'interface sur http://<IP_DE_TON_VPS>:3000"
