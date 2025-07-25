
# Solana AI Trading Bot - Frontend

Ce dossier contient l’application frontend React.js du bot Solana AI Trading. Il fournit une interface web pour surveiller l’activité du bot, visualiser les données de trading, gérer les paramètres et interagir avec la base de réputation.

## Technologies utilisées

- **React.js** : Librairie JavaScript pour construire des interfaces utilisateur modernes.
- **Tailwind CSS** : Framework CSS utilitaire pour un design rapide et personnalisable.
- **Headless UI** : Composants UI accessibles et non stylisés, parfaits avec Tailwind CSS.
- **React Router DOM** : Routage déclaratif pour les applications React.
- **Solana Web3.js & Wallet Adapters** : Pour une future interaction directe avec la blockchain Solana (affichage du solde, historique, etc.).

## Structure du projet

- `public/` : Contient les assets statiques (`index.html`, `favicon.ico`, manifest, etc.).
- `src/` : Code source principal de l’application React.
  - `components/` : Composants réutilisables (`Dashboard.js`, `Login.js`, `PrivateRoute.js`...)
  - `App.js` : Composant principal, gère le routage.
  - `index.js` : Point d’entrée de l’application React.
  - `App.css`, `index.css` : Import Tailwind CSS et styles globaux.
  - `reportWebVitals.js` : Mesure des performances.
  - `setupTests.js` : Configuration des tests.

## Scripts disponibles

Dans le dossier du projet, vous pouvez lancer :

- `yarn start` : Démarre l’application en mode développement.
- `yarn build` : Compile l’application pour la production dans le dossier `build`.
- `yarn test` : Lance le runner de tests.
- `yarn eject` : Retire la dépendance unique de build (avancé).

## Déploiement

Le frontend est conçu pour être compilé puis servi comme fichiers statiques par le backend FastAPI. Le `Dockerfile` à la racine du projet gère la compilation et la mise à disposition automatique de cette application frontend.