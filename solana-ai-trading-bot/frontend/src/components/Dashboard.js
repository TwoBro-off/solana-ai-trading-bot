  // Profits cumulés (simulation/réel)
  const [profits, setProfits] = useState({ profit_simulation: 0, profit_reel: 0 });
  useEffect(() => {
    const fetchProfits = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/profits', { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setProfits(data);
        }
      } catch {}
    };
    fetchProfits();
    const interval = setInterval(fetchProfits, 10000);
    return () => clearInterval(interval);
  }, []);
// ...existing code...

// Style Apple-like global pour glassmorphism
// À placer juste avant export default Dashboard;

const DashboardStyle = () => (
  <style>{`
    .glass-card {
      background: rgba(255,255,255,0.10);
      border-radius: 2rem;
      box-shadow: 0 8px 32px 0 rgba(31,38,135,0.18);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255,255,255,0.18);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 8px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(255,255,255,0.12);
      border-radius: 8px;
    }
    .animate-fadein-slow {
      animation: fadein 1.2s cubic-bezier(.39,.575,.565,1) both;
    }
    @keyframes fadein {
      0% { opacity: 0; transform: translateY(16px); }
      100% { opacity: 1; transform: none; }
    }
  `}</style>
);

  // --- État du bot et logs ---
  const [botStatus, setBotStatus] = useState({ mode: 'inconnu', capital: null, message: '' });
  const [recentLogs, setRecentLogs] = useState([]);
  const [alert, setAlert] = useState('');

  // Récupère l’état du bot et les logs récents périodiquement
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/dashboard', { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setBotStatus({
            mode: data.mode || 'inconnu',
            capital: data.solana_balance,
            message: data.status_message || ''
          });
        }
      } catch {}
    };
    const fetchLogs = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/logs/recent', { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setRecentLogs(data.logs || []);
        }
      } catch {}
    };
    fetchStatus();
    fetchLogs();
    const interval = setInterval(() => { fetchStatus(); fetchLogs(); }, 10000);
    return () => clearInterval(interval);
  }, []);
  // --- Mode réel temporaire : durée de trading réel ---
  const [realDays, setRealDays] = useState(0);
  const [realHours, setRealHours] = useState(0);
  const [realMsg, setRealMsg] = useState('');
  const handleRealStart = async () => {
    setRealMsg('');
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ai/start_real_mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ days: realDays, hours: realHours })
      });
      if (response.ok) {
        setRealMsg('Trading réel activé pour la période choisie.');
      } else {
        setRealMsg('Erreur lors de l’activation du trading réel.');
      }
    } catch (error) {
      setRealMsg('Erreur réseau ou serveur inaccessible');
    }
  };
  // --- Mode vacances : durée d'amélioration automatique ---
  const [vacationDays, setVacationDays] = useState(0);
  const [vacationHours, setVacationHours] = useState(0);
  const [vacationMsg, setVacationMsg] = useState('');
  const handleVacationStart = async () => {
    setVacationMsg('');
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/ai/start_vacation_mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ days: vacationDays, hours: vacationHours })
      });
      if (response.ok) {
        setVacationMsg('Mode vacances activé ! Le bot va s’auto-améliorer pendant la période choisie.');
      } else {
        setVacationMsg('Erreur lors de l’activation du mode vacances.');
      }
    } catch (error) {
      setVacationMsg('Erreur réseau ou serveur inaccessible');
    }
  };
import React, { useState, useEffect } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { FiRefreshCw, FiSearch, FiSun, FiMoon, FiInfo, FiEye, FiDollarSign } from 'react-icons/fi';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';
import { useNavigate } from 'react-router-dom';
import { Tab } from '@headlessui/react';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const Dashboard = () => {
  useEffect(() => {
    if (saleAlert) {
      toast.info(`Vente automatique du token ${saleAlert.token} (${saleAlert.reason})`, { position: 'top-right', autoClose: 4000 });
    }
  }, [saleAlert]);
  const [tradeHistory, setTradeHistory] = useState([]);
  // Récupère l'historique des trades
  const fetchTradeHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/trade-history', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setTradeHistory(data);
      }
    } catch (error) {
      toast.error('Erreur chargement historique des trades');
    }
  };
  const [theme, setTheme] = useState('dark');
  const [searchToken, setSearchToken] = useState('');
  const [filteredTokens, setFilteredTokens] = useState([]);
  useEffect(() => {
    setFilteredTokens(
      heldTokens.filter(token =>
        token.token_mint_address.toLowerCase().includes(searchToken.toLowerCase())
      )
    );
  }, [searchToken, heldTokens]);
  const [saleAlert, setSaleAlert] = useState(null);
  // Nouveaux états pour la sécurité des tokens
  const [heldTokens, setHeldTokens] = useState([]);
  const [securityThresholds, setSecurityThresholds] = useState({
    sell_multiplier: settings.SELL_MULTIPLIER || 2.0,
    trailing_stop_percent: settings.TRAILING_STOP_PERCENT || 0.15,
    stop_loss_multiplier: settings.STOP_LOSS_MULTIPLIER || 1.0,
  });

  // Récupère les tokens détenus (exemple, à adapter selon API backend)
  const fetchHeldTokens = async () => {
    // Simule une vente automatique pour l'exemple (à remplacer par API backend)
    // setSaleAlert({ token: 'TOKEN123', reason: 'Take Profit' });
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/held-tokens', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setHeldTokens(data);
      }
    } catch (error) {
      // ...
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchReputationEntries();
    fetchSettings();
    fetchHeldTokens();
    fetchTradeHistory();
  }, []);
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [manualWalletId, setManualWalletId] = useState('');
  const [manualTags, setManualTags] = useState('');
  const [manualComportement, setManualComportement] = useState('');
  const [manualScore, setManualScore] = useState('');
  const [message, setMessage] = useState('');
  const [reputationEntries, setReputationEntries] = useState([]);
  const [trustwalletAutoValidation, setTrustwalletAutoValidation] = useState(true);
  // Paramètres avancés
  const [settings, setSettings] = useState({});
  const [settingsMessage, setSettingsMessage] = useState('');
  // Regroupement des paramètres par catégories pour une interface épurée
  const settingsCategories = [
    {
      name: 'Trading',
      params: [
        { key: 'INITIAL_CAPITAL_SOL', label: 'Capital initial (SOL)', type: 'number', step: 0.01 },
        { key: 'MIN_LIQUIDITY_POOL_SOL', label: 'Liquidité min. pool (SOL)', type: 'number', step: 0.01 },
        { key: 'BUY_AMOUNT_SOL', label: 'Montant achat (SOL)', type: 'number', step: 0.01 },
        { key: 'SELL_MULTIPLIER', label: 'Multiplicateur vente', type: 'number', step: 0.01 },
        { key: 'PROFIT_MULTIPLIER_SELL', label: 'Multiplicateur profit vente', type: 'number', step: 0.01 },
        { key: 'STOP_LOSS_PROFIT_MULTIPLIER', label: 'Multiplicateur stop loss', type: 'number', step: 0.01 },
      ],
    },
    {
      name: 'Sécurité',
      params: [
        { key: 'REPUTATION_SCORE_THRESHOLD', label: 'Seuil réputation', type: 'number', step: 0.01 },
        { key: 'PRIVATE_KEY', label: 'Clé privée', type: 'password' },
        { key: 'WALLET_ADDRESS', label: 'Adresse du portefeuille', type: 'text' },
      ],
    },
    {
      name: 'Simulation',
      params: [
        { key: 'SIMULATION_MODE', label: 'Mode simulation', type: 'switch' },
        { key: 'SIMULATION_REPORT_PATH', label: 'Chemin rapport simulation', type: 'text' },
      ],
    },
    {
      name: 'Blockchain',
      params: [
        { key: 'SOLANA_RPC_URL', label: 'Solana RPC URL', type: 'text' },
        { key: 'SOLANA_WS_URL', label: 'Solana WebSocket URL', type: 'text' },
        { key: 'JITO_SHREDSTREAM_GRPC_URL', label: 'Jito Shredstream gRPC', type: 'text' },
        { key: 'HELIUS_API_KEY', label: 'Helius API Key', type: 'password' },
        { key: 'RPC_LATENCY_CHECK_INTERVAL', label: 'Intervalle latence RPC (s)', type: 'number', step: 1 },
        { key: 'TOKEN_SCAN_INTERVAL', label: 'Intervalle scan token (s)', type: 'number', step: 1 },
        { key: 'LATENCY_TARGET_MS', label: 'Latence cible (ms)', type: 'number', step: 1 },
      ],
    },
    {
      name: 'AI',
      params: [
        { key: 'OPENROUTER_API_KEY', label: 'OpenRouter API Key', type: 'password' },
        { key: 'GEMINI_MODEL', label: 'Modèle Gemini', type: 'text' },
      ],
    },
    {
      name: 'Système',
      params: [
        { key: 'LOG_LEVEL', label: 'Niveau de log', type: 'select', options: ['DEBUG','INFO','WARNING','ERROR'] },
        { key: 'DATABASE_URL', label: 'URL base de données', type: 'text' },
      ],
    },
  ];
  const handleTrustwalletValidationChange = async (e) => {
    setTrustwalletAutoValidation(e.target.checked);
    // Appel backend pour configurer le mode
    const token = localStorage.getItem('token');
    await fetch('/api/trustwallet-validation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ auto_validation: e.target.checked }),
    });
  };

  useEffect(() => {
    fetchDashboardData();
    fetchReputationEntries();
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/settings', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      setSettingsMessage('Erreur chargement paramètres');
    }
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSettingsSave = async (e) => {
    e.preventDefault();
    setSettingsMessage('');
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(settings),
      });
      if (response.ok) {
        setSettingsMessage('Paramètres mis à jour !');
        fetchSettings();
      } else {
        setSettingsMessage('Erreur lors de la mise à jour');
      }
    } catch (error) {
      setSettingsMessage('Erreur réseau ou serveur inaccessible');
    }
  };

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      } else if (response.status === 401) {
        navigate('/login');
      } else {
        console.error('Failed to fetch dashboard data');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  const fetchReputationEntries = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/reputation-db', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setReputationEntries(data);
      } else if (response.status === 401) {
        navigate('/login');
      } else {
        console.error('Failed to fetch reputation entries');
      }
    } catch (error) {
      console.error('Error fetching reputation entries:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleGeminiApiKeyUpdate = async (e) => {
    e.preventDefault();
    setMessage('');
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/gemini-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ gemini_api_key: geminiApiKey }),
      });
      if (response.ok) {
        setMessage('Clé API Gemini mise à jour avec succès !');
      } else {
        const errData = await response.json();
        setMessage(`Échec de la mise à jour de la clé API : ${errData.detail || 'Erreur inconnue'}`);
      }
    } catch (error) {
      setMessage('Erreur réseau ou serveur inaccessible');
    }
  };

  const handleManualReputationEntry = async (e) => {
    e.preventDefault();
    setMessage('');
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/manual-reputation-entry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          wallet_id: manualWalletId,
          ip_publique: null,
          tags: manualTags.split(',').map(tag => tag.trim()),
          comportement: manualComportement,
          score_de_confiance: parseFloat(manualScore),
        }),
      });
      if (response.ok) {
        setMessage('Entrée de réputation manuelle ajoutée avec succès !');
        setManualWalletId('');
        setManualTags('');
        setManualComportement('');
        setManualScore('');
        fetchReputationEntries(); // Refresh the list
      } else {
        const errData = await response.json();
        setMessage(`Échec de l'ajout de l'entrée : ${errData.detail || 'Erreur inconnue'}`);
      }
    } catch (error) {
      setMessage('Network error or server is unreachable');
    }
  };

  const [initialCapital, setInitialCapital] = useState(100); // Valeur par défaut

  const handleInitialCapitalChange = (e) => {
    setInitialCapital(e.target.value);
  };

  const handleSetInitialCapital = async () => {
    await fetch('/api/decision/set_initial_capital', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: initialCapital })
    });
    // Optionnel : afficher une notification de succès
  };

  return (
    <div className={theme === 'dark' ? "min-h-screen bg-gray-900 text-white p-8 transition-colors duration-300" : "min-h-screen bg-gray-100 text-gray-900 p-8 transition-colors duration-300"}>
      <div className="flex justify-end mb-4">
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="mr-2 p-2 rounded-full bg-gray-700 hover:bg-gray-600 transition-colors" title="Changer de thème">
          {theme === 'dark' ? <FiSun size={20} /> : <FiMoon size={20} />}
        </button>
      </div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Tableau de Bord du Bot de Trading IA Solana</h1>
        <div className="flex items-center space-x-4">
          <a href="/chat" className="bg-blue-700 hover:bg-blue-800 text-white font-bold py-2 px-4 rounded transition-colors">💬 Chat Gemini IA</a>
          <button
            onClick={handleLogout}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            Déconnexion
          </button>
        </div>
      </div>

      <Tab.Group>
        <Tab.List className="flex p-1 space-x-1 bg-blue-900/20 rounded-xl mb-8">
          <Tab
            className={({ selected }) =>
              classNames(
                'w-full py-2.5 text-sm leading-5 font-medium text-blue-700 rounded-lg',
                'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60',
                selected
                  ? 'bg-white shadow'
                  : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
              )
            }
          >
            Aperçu
          </Tab>
          <Tab
            className={({ selected }) =>
              classNames(
                'w-full py-2.5 text-sm leading-5 font-medium text-blue-700 rounded-lg',
                'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60',
                selected
                  ? 'bg-white shadow'
                  : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
              )
            }
          >
            Paramètres
          </Tab>
          <Tab
            className={({ selected }) =>
              classNames(
                'w-full py-2.5 text-sm leading-5 font-medium text-blue-700 rounded-lg',
                'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60',
                selected
                  ? 'bg-white shadow'
                  : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
              )
            }
          >
            BD de Réputation
          </Tab>
        </Tab.List>
        <Tab.Panels className="mt-2">
        <div className="mb-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={trustwalletAutoValidation}
              onChange={handleTrustwalletValidationChange}
              className="form-checkbox h-5 w-5 text-blue-600"
            />
            <span>Validation automatique TrustWallet (simulation rapide)</span>
          </label>
        </div>
          <Tab.Panel
            className={classNames(
              'rounded-xl bg-gray-800 p-3',
              'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60'
            )}
          >
            <h2 className="text-2xl font-bold mb-4">Aperçu du Bot</h2>
            {dashboardData ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Solde du Portefeuille</h3>
                  <p className="text-lg">{dashboardData.sol_balance} SOL</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Profit total (réel)</h3>
                  <p className="text-lg text-green-400">{profits.profit_reel} SOL</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Profit total (simulation)</h3>
                  <p className="text-lg text-blue-400">{profits.profit_simulation} SOL</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Latence RPC</h3>
                  <p className="text-lg">{dashboardData.rpc_latency} ms</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Tokens analysés</h3>
                  <p className="text-lg">{dashboardData.tokens_scanned}</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Trades exécutés</h3>
                  <p className="text-lg">{dashboardData.trades_executed}</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Statut analyse IA</h3>
                  <p className="text-lg">{dashboardData.ai_analysis_status}</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h3 className="text-xl font-semibold">Santé système</h3>
                  <p className="text-lg">{dashboardData.system_health}</p>
                </div>
              </div>
            ) : (
              <p>Chargement des données du tableau de bord...</p>
            )}
            {/* Tableau des tokens détenus avec indicateurs de sécurité */}
            <div className="flex items-center mb-2">
              <h3 className="text-xl font-bold">Tokens détenus</h3>
              <div className="ml-auto flex items-center space-x-2">
                <input
                  type="text"
                  placeholder="Rechercher un token..."
                  value={searchToken}
                  onChange={e => setSearchToken(e.target.value)}
                  className={theme === 'dark' ? "px-2 py-1 rounded bg-gray-800 text-white border border-gray-700" : "px-2 py-1 rounded bg-gray-200 text-gray-900 border border-gray-400"}
                />
                <button onClick={fetchHeldTokens} className="p-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white transition-colors" title="Rafraîchir">
                  <FiRefreshCw size={18} />
                </button>
              </div>
            </div>
            <div className="overflow-x-auto mb-6">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Token</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Prix d'achat</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Prix actuel</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Max atteint</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Take Profit</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Trailing Stop</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Stop Loss</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Statut</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Graphique</th>
                  </tr>
                </thead>
                <tbody className="bg-gray-800 divide-y divide-gray-700">
                  {filteredTokens.length > 0 ? filteredTokens.map(token => {
                    const profitMultiplier = token.current_price / token.buy_price;
                    let status = 'Sécurisé';
                    let badge = 'bg-green-700';
                    if (profitMultiplier >= securityThresholds.sell_multiplier) {
                      status = 'Take Profit'; badge = 'bg-blue-700';
                      setSaleAlert({ token: token.token_mint_address, reason: 'Take Profit' });
                    } else if (token.current_price < token.max_price * (1 - securityThresholds.trailing_stop_percent)) {
                      status = 'Trailing Stop'; badge = 'bg-yellow-700';
                      setSaleAlert({ token: token.token_mint_address, reason: 'Trailing Stop' });
                    } else if (profitMultiplier < securityThresholds.stop_loss_multiplier) {
                      status = 'Stop Loss'; badge = 'bg-red-700';
                      setSaleAlert({ token: token.token_mint_address, reason: 'Stop Loss' });
                    }
                    // Graphique d'évolution du prix (exemple, à adapter selon backend)
                    const priceHistory = token.price_history || [token.buy_price, token.current_price];
                    const chartData = {
                      labels: priceHistory.map((_, i) => i + 1),
                      datasets: [{
                        label: 'Prix',
                        data: priceHistory,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59,130,246,0.1)',
                        tension: 0.3,
                      }],
                    };
                    return (
                      <tr key={token.token_mint_address} className="hover:bg-blue-900/10 transition-colors">
                        <td className="px-4 py-2 text-sm font-semibold flex items-center space-x-2">
                          {token.token_mint_address}
                          <span className="ml-1" title="Voir détails"><FiEye size={16} /></span>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-300 flex items-center">
                          {token.buy_price}
                          <span className="ml-1" title="Prix d'achat"><FiInfo size={14} /></span>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-300">{token.current_price}</td>
                        <td className="px-4 py-2 text-sm text-gray-300">{token.max_price}</td>
                        <td className="px-4 py-2 text-sm text-gray-300">x{securityThresholds.sell_multiplier}</td>
                        <td className="px-4 py-2 text-sm text-gray-300">{parseInt(securityThresholds.trailing_stop_percent*100)}%</td>
                        <td className="px-4 py-2 text-sm text-gray-300">x{securityThresholds.stop_loss_multiplier}</td>
                        <td className={`px-4 py-2 text-sm font-bold rounded ${badge}`}>{status}</td>
                        <td className="px-4 py-2">
                          <div style={{ width: 120, height: 60 }}>
                            <Line data={chartData} options={{ plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } }} />
                          </div>
                        </td>
                        <td className="px-4 py-2 flex space-x-2">
                          <button className="p-1 rounded bg-green-600 hover:bg-green-700 text-white transition-colors" title="Vendre manuellement"><FiDollarSign size={16} /></button>
                          <button className="p-1 rounded bg-gray-600 hover:bg-gray-700 text-white transition-colors" title="Voir historique"><FiEye size={16} /></button>
                        </td>
                      </tr>
                    );
                  }) : (
                    <tr><td colSpan={11} className="px-4 py-2 text-center text-gray-400">Aucun token détenu</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {/* Alerte animée lors d'une vente automatique */}
            {/* La notification toast est gérée par useEffect */}
            {/* Tableau historique des trades */}
            <h3 className="text-xl font-bold mb-2 mt-8">Historique des trades</h3>
            <div className="overflow-x-auto mb-6">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Date</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Token</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Action</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Prix</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Montant</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">Profit</th>
                  </tr>
                </thead>
                <tbody className="bg-gray-800 divide-y divide-gray-700">
                  {tradeHistory.length > 0 ? tradeHistory.map(trade => (
                    <tr key={trade.id} className="hover:bg-blue-900/10 transition-colors">
                      <td className="px-4 py-2 text-sm text-gray-300">{new Date(trade.timestamp).toLocaleString()}</td>
                      <td className="px-4 py-2 text-sm text-white">{trade.token_mint_address}</td>
                      <td className="px-4 py-2 text-sm font-bold text-blue-400">{trade.action}</td>
                      <td className="px-4 py-2 text-sm text-gray-300">{trade.price}</td>
                      <td className="px-4 py-2 text-sm text-gray-300">{trade.amount}</td>
                      <td className="px-4 py-2 text-sm text-green-400">{trade.profit}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan={6} className="px-4 py-2 text-center text-gray-400">Aucun trade enregistré</td></tr>
                  )}
                </tbody>
              </table>
            </div>
      <ToastContainer />
          </Tab.Panel>
          <Tab.Panel
            className={classNames(
              'rounded-xl bg-gray-800 p-3',
              'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60'
            )}
          >
            <h2 className="text-2xl font-bold mb-4">Paramètres du Bot</h2>
            {/* État du bot */}
            <div className="mb-4 p-4 bg-gray-900/40 rounded-lg flex items-center space-x-6">
              <div>
                <span className={`inline-block w-3 h-3 rounded-full mr-2 ${botStatus.mode === 'réel' ? 'bg-green-500' : botStatus.mode === 'simulation' ? 'bg-blue-500' : 'bg-gray-400'}`}></span>
                <span className="font-bold">Mode&nbsp;:</span> {botStatus.mode}
              </div>
              <div>
                <span className="font-bold">Capital restant&nbsp;:</span> {botStatus.capital !== null ? `${botStatus.capital} SOL` : '...'}
              </div>
              {botStatus.message && <div className="text-yellow-400">{botStatus.message}</div>}
            </div>

            {/* Alertes */}
            {alert && <div className="mb-2 p-2 bg-red-700/80 text-white rounded">{alert}</div>}

            <form onSubmit={handleSettingsSave} className="space-y-2">
            {/* Logs récents */}
            <div className="mt-6 bg-gray-900/30 rounded-lg p-4">
              <h3 className="font-bold mb-2 text-sm text-gray-300">Logs récents</h3>
              <div className="max-h-40 overflow-y-auto text-xs text-gray-400">
                {recentLogs.length === 0 ? <div>Aucun log récent.</div> : recentLogs.map((log, i) => (
                  <div key={i} className="mb-1 whitespace-pre-line">{log}</div>
                ))}
              </div>
            </div>
              {/* Bloc de configuration du mode vacances */}
              {/* Bloc de configuration du mode réel temporaire */}
              <div className="mb-4 p-4 bg-green-900/20 rounded-lg">
                <h3 className="text-lg font-bold mb-2">Mode réel temporaire (trading avec vrai capital)</h3>
                <div className="flex items-center space-x-4 mb-2">
                  <label htmlFor="realDays" className="text-sm font-medium text-gray-300">Jours :</label>
                  <input type="number" id="realDays" min="0" max="30" value={realDays} onChange={e => setRealDays(Number(e.target.value))} className="w-16 rounded bg-gray-800 border-gray-700 text-white px-2" />
                  <label htmlFor="realHours" className="text-sm font-medium text-gray-300">Heures :</label>
                  <input type="number" id="realHours" min="0" max="23" value={realHours} onChange={e => setRealHours(Number(e.target.value))} className="w-16 rounded bg-gray-800 border-gray-700 text-white px-2" />
                  <button type="button" onClick={handleRealStart} className="bg-green-600 hover:bg-green-700 text-white font-bold py-1 px-4 rounded">Démarrer</button>
                </div>
                {realMsg && <div className="text-green-400 mt-2">{realMsg}</div>}
                <div className="text-xs text-gray-400 mt-1">Le bot effectuera des trades réels uniquement pendant cette période, puis repassera en simulation automatiquement.</div>
              </div>
              <div className="mb-4 p-4 bg-blue-900/20 rounded-lg">
                <h3 className="text-lg font-bold mb-2">Mode vacances (autoamélioration continue)</h3>
                <div className="flex items-center space-x-4 mb-2">
                  <label htmlFor="vacationDays" className="text-sm font-medium text-gray-300">Jours :</label>
                  <input type="number" id="vacationDays" min="0" max="30" value={vacationDays} onChange={e => setVacationDays(Number(e.target.value))} className="w-16 rounded bg-gray-800 border-gray-700 text-white px-2" />
                  <label htmlFor="vacationHours" className="text-sm font-medium text-gray-300">Heures :</label>
                  <input type="number" id="vacationHours" min="0" max="23" value={vacationHours} onChange={e => setVacationHours(Number(e.target.value))} className="w-16 rounded bg-gray-800 border-gray-700 text-white px-2" />
                  <button type="button" onClick={handleVacationStart} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-1 px-4 rounded">Démarrer</button>
                </div>
                {vacationMsg && <div className="text-green-400 mt-2">{vacationMsg}</div>}
                <div className="text-xs text-gray-400 mt-1">Pendant cette période, le bot tournera en simulation 24h/24 et s’auto-optimisera. À votre retour, il sera prêt !</div>
              </div>
              {settingsCategories.map(category => (
                <details key={category.name} className="mb-2 bg-gray-700 rounded-lg">
                  <summary className="cursor-pointer py-2 px-4 font-semibold text-blue-300 select-none focus:outline-none">{category.name}</summary>
                  <div className="p-4 space-y-2">
                    {category.params.map(param => (
                      <div key={param.key} className="flex items-center space-x-4">
                        <label htmlFor={param.key} className="block text-sm font-medium text-gray-300 w-64">{param.label}</label>
                        {param.type === 'text' || param.type === 'password' ? (
                          <input
                            type={param.type}
                            id={param.key}
                            className="mt-1 block w-full rounded-md bg-gray-800 border-gray-700 text-white focus:border-blue-500 focus:ring-blue-500"
                            value={settings[param.key] || ''}
                            onChange={e => handleSettingChange(param.key, e.target.value)}
                          />
                        ) : param.type === 'number' ? (
                          <input
                            type="number"
                            id={param.key}
                            step={param.step}
                            className="mt-1 block w-full rounded-md bg-gray-800 border-gray-700 text-white focus:border-blue-500 focus:ring-blue-500"
                            value={settings[param.key] || ''}
                            onChange={e => handleSettingChange(param.key, e.target.value)}
                          />
                        ) : param.type === 'select' ? (
                          <select
                            id={param.key}
                            className="mt-1 block w-full rounded-md bg-gray-800 border-gray-700 text-white focus:border-blue-500 focus:ring-blue-500"
                            value={settings[param.key] || param.options[0]}
                            onChange={e => handleSettingChange(param.key, e.target.value)}
                          >
                            {param.options.map(opt => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        ) : param.type === 'switch' ? (
                          <input
                            type="checkbox"
                            id={param.key}
                            checked={!!settings[param.key]}
                            onChange={e => handleSettingChange(param.key, e.target.checked)}
                            className="form-checkbox h-5 w-5 text-blue-600"
                          />
                        ) : null}
                      </div>
                    ))}
                  </div>
                </details>
              ))}
              <button
                type="submit"
                className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mt-2"
              >
                Enregistrer
              </button>
            </form>
            {settingsMessage && <div className="fixed bottom-4 right-4 bg-gray-900 text-green-400 px-4 py-2 rounded shadow-lg z-50 animate-fadein">{settingsMessage}</div>}
          </Tab.Panel>
          <Tab.Panel
            className={classNames(
              'rounded-xl bg-gray-800 p-3',
              'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-blue-400 ring-white ring-opacity-60'
            )}
          >
            <h2 className="text-2xl font-bold mb-4">Base de Données de Réputation</h2>
            <form onSubmit={handleManualReputationEntry} className="space-y-4 mb-8 p-4 bg-gray-700 rounded-lg">
              <h3 className="text-xl font-semibold mb-2">Ajouter une Entrée Manuelle</h3>
              <div>
                <label htmlFor="manualWalletId" className="block text-sm font-medium text-gray-300">ID du Portefeuille</label>
                <input
                  type="text"
                  id="manualWalletId"
                  className="mt-1 block w-full rounded-md bg-gray-600 border-gray-500 text-white focus:border-blue-500 focus:ring-blue-500"
                  value={manualWalletId}
                  onChange={(e) => setManualWalletId(e.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="manualTags" className="block text-sm font-medium text-gray-300">Tags (séparés par des virgules)</label>
                <input
                  type="text"
                  id="manualTags"
                  className="mt-1 block w-full rounded-md bg-gray-600 border-gray-500 text-white focus:border-blue-500 focus:ring-blue-500"
                  value={manualTags}
                  onChange={(e) => setManualTags(e.target.value)}
                  placeholder="e.g., scam, rugpull, trusted"
                />
              </div>
              <div>
                <label htmlFor="manualComportement" className="block text-sm font-medium text-gray-300">Comportement</label>
                <input
                  type="text"
                  id="manualComportement"
                  className="mt-1 block w-full rounded-md bg-gray-600 border-gray-500 text-white focus:border-blue-500 focus:ring-blue-500"
                  value={manualComportement}
                  onChange={(e) => setManualComportement(e.target.value)}
                  placeholder="e.g., malicious, legitimate"
                />
              </div>
              <div>
                <label htmlFor="manualScore" className="block text-sm font-medium text-gray-300">Score de Confiance (0.0-1.0)</label>
                <input
                  type="number"
                  id="manualScore"
                  step="0.01"
                  min="0"
                  max="1"
                  className="mt-1 block w-full rounded-md bg-gray-600 border-gray-500 text-white focus:border-blue-500 focus:ring-blue-500"
                  value={manualScore}
                  onChange={(e) => setManualScore(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
              >
                Ajouter l'entrée
              </button>
            </form>

            <h3 className="text-xl font-semibold mb-4">Entrées Existantes</h3>
            {reputationEntries.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-700">
                  <thead className="bg-gray-700">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">ID du Portefeuille</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">IP Publique</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Tags</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Comportement</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Score</th>
                    </tr>
                  </thead>
                  <tbody className="bg-gray-800 divide-y divide-gray-700">
                    {reputationEntries.map((entry) => (
                      <tr key={entry.wallet_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{entry.wallet_id}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{entry.ip_publique}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{entry.tags.join(', ')}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{entry.comportement}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{entry.score_de_confiance}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No reputation entries found.</p>
            )}
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
      <DashboardStyle />
    </div>
  );
};

export default Dashboard;