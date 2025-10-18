import React, { useState, useEffect, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';
import ErrorBoundary from './ErrorBoundary.js'; // Importer le nouveau composant

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const OFFLINE_STATUS = { is_running: false, current_mode: 'Déconnecté', is_offline: true };

function DashboardContent() {
  const [botStatus, setBotStatus] = useState(OFFLINE_STATUS);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [simulationData, setSimulationData] = useState({ trade_history: [] });
  const [readiness, setReadiness] = useState({ is_ready: false, checks: {}, missing_items: [] });

  const fetchBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/status`);
      if (!response.ok) {
        console.error('Backend error:', response.status);
        throw new Error('Backend not responding');
      }
      const data = await response.json();
      setBotStatus(data);
      if (error) setError('');
      return data; // **CORRECTION : Retourner les données pour la logique séquentielle**
    } catch (err) {
      console.error('Failed to fetch bot status:', err);
      setBotStatus(OFFLINE_STATUS);
      setError('Impossible de contacter le backend. Vérifiez que le serveur est en cours d\'exécution.');
      return null; // **CORRECTION : Retourner null en cas d'échec**
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [error, setBotStatus, setError]); // Correctly include error dependency

  const fetchSimulationData = useCallback(async () => {
    if (botStatus.is_running && botStatus.current_mode === 'simulation' && !botStatus.is_offline) {
      try {
        const response = await fetch(`${API_URL}/api/simulation/dashboard`);
        if (!response.ok) return;
        const data = await response.json();
        setSimulationData(data);
      } catch (err) { /* Fail silently, status check will handle it */ }
    }
  }, [botStatus]);
  
  const fetchReadiness = useCallback(async () => {
    if (!botStatus || botStatus.is_offline) return; // Plus robuste
    try {
      const response = await fetch(`${API_URL}/api/bot/readiness`);
      if (!response.ok) return;
      const data = await response.json();
      setReadiness(data);
    } catch (err) { /* fail silently */ }
  }, [botStatus]); // Dépendance plus sûre

  useEffect(() => {
    // Effet unifié pour gérer tout le cycle de vie du polling de données.
    const updateData = async () => {
      // 1. Toujours récupérer le statut le plus récent
      const status = await fetchBotStatus(); // This was correct, but let's ensure it's robust
      if (isPageLoading) setIsPageLoading(false);

      // 2. Décider quelles données supplémentaires chercher en fonction du statut
      if (status && status.is_running && status.current_mode === 'simulation') {
        fetchSimulationData(); // Pas besoin d'await ici, on peut les lancer en parallèle
      } else if (status && !status.is_running) {
        fetchReadiness(); // Pas besoin d'await ici
      } else {
        setSimulationData({ trade_history: [] }); // Clear data if bot is offline or in an unknown state
      }
    }

    updateData(); // Appel initial
    const interval = setInterval(updateData, 5000);
    return () => clearInterval(interval);
  }, [fetchBotStatus, isPageLoading, fetchSimulationData, fetchReadiness]); // Correctly include all dependencies

  const handleStart = async (mode) => {
    if (isLoading || botStatus?.is_running || botStatus?.is_offline) return; // **CORRECTION : Utiliser le chaînage optionnel pour la robustesse**
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/api/bot/start?mode=${mode}`, { method: 'POST' });
      if (!response.ok) throw new Error((await response.json()).detail || 'Failed to start bot');
      setTimeout(fetchBotStatus, 1000);
    } catch (err) { setError(err.message); } 
    finally { setIsLoading(false); }
  };

  const handleStartRealWithConfirmation = () => {
    const confirmationMessage = "Êtes-vous sûr de vouloir démarrer le bot en MODE RÉEL ?\n\n" +
                                "Cela engagera des fonds réels et peut entraîner des pertes financières. " +
                                "Assurez-vous d'avoir bien testé en mode simulation et de comprendre les risques.";
    
    if (window.confirm(confirmationMessage)) {
      handleStart('real');
    }
  };

  const handleStop = async () => {
    if (isLoading || !botStatus?.is_running || botStatus?.is_offline) return; // **CORRECTION : Utiliser le chaînage optionnel pour la robustesse**
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/api/bot/stop`, { method: 'POST' });
      if (!response.ok) throw new Error((await response.json()).detail || 'Failed to stop bot');
      setTimeout(fetchBotStatus, 1000);
    } catch (err) { setError(err.message); } 
    finally { setIsLoading(false); }
  };

  if (isPageLoading) {
    return <div className="flex items-center justify-center h-[calc(100vh-4rem)]"><p className="text-gray-500">Connexion au serveur...</p></div>;
  }

  // S'assurer que trade_history est toujours un tableau pour éviter les erreurs de rendu.
  const tradeHistory = Array.isArray(simulationData?.trade_history) ? simulationData.trade_history : [];

  const chartData = {
    labels: tradeHistory.map(t => new Date(t.timestamp * 1000).toLocaleTimeString()),
    datasets: [{
      label: 'Profit/Perte Cumulé (SOL)',
      data: tradeHistory.reduce((acc, trade, index, array) => {
        const lastPnl = acc.length > 0 ? acc[acc.length - 1] : 0.0;
        let pnl = lastPnl;
        if (trade.action === 'sell') {
            const buyTrade = array.slice(0, index).reverse().find(t => t.token === trade.token && t.action === 'buy');
            // Vérification robuste pour éviter les erreurs de rendu
            if (buyTrade && typeof trade.price === 'number' && typeof buyTrade.price === 'number') {
                const tradePnl = trade.price - buyTrade.price;
                // S'assurer que le résultat est un nombre valide
                if (!isNaN(tradePnl)) {
                    pnl += tradePnl;
                }
            }
        }
        acc.push(pnl);
        return acc;
      }, []),
      borderColor: 'rgb(14, 165, 233)', // sky-500
      backgroundColor: 'rgba(14, 165, 233, 0.1)',
      tension: 0.3,
      fill: true,
    }],
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Colonne de gauche: Contrôles et Statut */}
        <div className="lg:col-span-1 space-y-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Centre de Contrôle</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-gray-100 p-3 rounded-lg" data-testid="bot-status-display">
                <span className="text-sm text-gray-600">Statut du Bot</span>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${botStatus?.is_running ? 'bg-green-100 text-green-800' : botStatus?.is_offline ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                  {botStatus?.is_running ? `Actif: ${botStatus?.current_mode}` : botStatus?.is_offline ? 'Déconnecté' : 'Arrêté'}
                </span>
              </div>
              <div className="pt-2">
                {botStatus?.is_running ? (
                  <button onClick={handleStop} disabled={isLoading} className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                    {isLoading ? 'Arrêt en cours...' : 'Arrêter le Bot'}
                  </button>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <button onClick={() => handleStart('simulation')} disabled={isLoading || botStatus?.is_offline} className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {isLoading ? '...' : 'Simulation'}
                    </button>
                    <button onClick={handleStartRealWithConfirmation} disabled={isLoading || botStatus?.is_offline || !readiness.is_ready} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {isLoading ? '...' : 'Mode Réel'}
                    </button>
                  </div>
                )}
              </div>
              {error && <p className="text-xs text-red-600 text-center pt-2">{error}</p>}
            </div>
          </div>

          {!botStatus?.is_running && (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Préparation au Mode Réel</h3>
              <ul className="space-y-2 text-sm">
                {(() => {
                    const labels = {
                        private_key_set: 'Clé privée configurée', //NOSONAR
                        wallet_address_set: 'Adresse de wallet configurée',
                        helius_key_set: 'Clé Helius configurée (Recommandé)', //NOSONAR
                        initial_balance_ok: `Solde suffisant (actuel: ${typeof readiness.checks?.balance_sol === 'number' ? readiness.checks.balance_sol.toFixed(4) : 'N/A'} SOL)`,
                    };
                    return Object.entries(labels).map(([key, label]) => {
                        const isChecked = readiness.checks?.[key] === true;
                        return (
                            <li key={key} className="flex items-center"><span className={`mr-2 ${isChecked ? 'text-green-500' : 'text-red-500'}`}>{isChecked ? '✓' : '✗'}</span> {label}</li>
                        );
                    });
                })()}
              </ul>
            </div>
          )}

          {botStatus?.is_running && botStatus?.current_mode === 'simulation' && (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance (Simulation)</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Profit / Perte</span><span className={`font-semibold ${simulationData?.profit_loss_sol >= 0 ? 'text-green-600' : 'text-red-600'}`}>{simulationData?.profit_loss_sol?.toFixed(4) || '0.0000'} SOL</span></div>
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Trades</span><span className="font-semibold text-gray-800">{simulationData?.total_trades || 0}</span></div>
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Positions Ouvertes</span><span className="font-semibold text-gray-800">{simulationData?.held_tokens_count || 0}</span></div>
              </div>
            </div>
          )}

        </div>

        {/* Colonne de droite: Graphiques et Logs */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance en Temps Réel</h3>
            <div className="h-80">
              {tradeHistory.length > 0 ? (
                <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#6b7280' } }, y: { ticks: { color: '#6b7280' } } } }} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                  {botStatus?.is_running ? 'En attente de données de trading...' : 'Démarrez une session pour voir les performances.'}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          </div>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  return (
    <ErrorBoundary>
      <DashboardContent />
    </ErrorBoundary>
  );
}

export default Dashboard;
