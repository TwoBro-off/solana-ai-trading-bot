import React, { useState, useEffect, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const OFFLINE_STATUS = { is_running: false, current_mode: 'Déconnecté', is_offline: true };

function Dashboard() {
  const [botStatus, setBotStatus] = useState(OFFLINE_STATUS);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [simulationData, setSimulationData] = useState(null);

  const fetchBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/status`);
      if (!response.ok) throw new Error('Backend not responding');
      const data = await response.json();
      setBotStatus(data);
      if (error) setError('');
    } catch (err) {
      setBotStatus(OFFLINE_STATUS);
    }
  }, [error]);

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

  useEffect(() => {
    const initialFetch = async () => {
      await fetchBotStatus();
      setIsPageLoading(false);
    };
    initialFetch();
    const interval = setInterval(fetchBotStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchBotStatus]);

  useEffect(() => {
    if (botStatus.is_running && botStatus.current_mode === 'simulation') {
      fetchSimulationData();
      const simInterval = setInterval(fetchSimulationData, 5000);
      return () => clearInterval(simInterval);
    } else {
      setSimulationData(null);
    }
  }, [botStatus, fetchSimulationData]);

  const handleStart = async (mode) => {
    if (isLoading || botStatus.is_running || botStatus.is_offline) return;
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/api/bot/start?mode=${mode}`, { method: 'POST' });
      if (!response.ok) throw new Error((await response.json()).detail || 'Failed to start bot');
      setTimeout(fetchBotStatus, 1000);
    } catch (err) { setError(err.message); } 
    finally { setIsLoading(false); }
  };

  const handleStop = async () => {
    if (isLoading || !botStatus.is_running || botStatus.is_offline) return;
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

  const chartData = {
    labels: simulationData?.trade_history.map(t => new Date(t.timestamp * 1000).toLocaleTimeString()) || [],
    datasets: [{
      label: 'Profit/Perte Cumulé (SOL)',
      data: (simulationData?.trade_history || []).reduce((acc, trade) => {
        const lastPnl = acc.length > 0 ? acc[acc.length - 1] : 0;
        const pnlChange = trade.action === 'buy' ? -trade.price : trade.price;
        acc.push(lastPnl + pnlChange);
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Colonne de gauche: Contrôles et Statut */}
        <div className="lg:col-span-1 space-y-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Centre de Contrôle</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-gray-100 p-3 rounded-lg">
                <span className="text-sm text-gray-600">Statut du Bot</span>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${botStatus.is_running ? 'bg-green-100 text-green-800' : botStatus.is_offline ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                  {botStatus.is_running ? `Actif: ${botStatus.current_mode}` : botStatus.is_offline ? 'Déconnecté' : 'Arrêté'}
                </span>
              </div>
              <div className="pt-2">
                {botStatus.is_running ? (
                  <button onClick={handleStop} disabled={isLoading} className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                    {isLoading ? 'Arrêt en cours...' : 'Arrêter le Bot'}
                  </button>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <button onClick={() => handleStart('simulation')} disabled={isLoading || botStatus.is_offline} className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {isLoading ? '...' : 'Simulation'}
                    </button>
                    <button onClick={() => handleStart('real')} disabled={isLoading || botStatus.is_offline} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                      {isLoading ? '...' : 'Mode Réel'}
                    </button>
                  </div>
                )}
              </div>
              {error && <p className="text-xs text-red-600 text-center pt-2">{error}</p>}
            </div>
          </div>

          {simulationData && (
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance (Simulation)</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Profit / Perte</span><span className={`font-semibold ${simulationData.profit_loss_sol >= 0 ? 'text-green-600' : 'text-red-600'}`}>{simulationData.profit_loss_sol.toFixed(4)} SOL</span></div>
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Trades</span><span className="font-semibold text-gray-800">{simulationData.total_trades}</span></div>
                <div className="flex justify-between items-baseline"><span className="text-sm text-gray-500">Positions Ouvertes</span><span className="font-semibold text-gray-800">{simulationData.held_tokens_count}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Colonne de droite: Graphique et Logs */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Activité de Trading</h3>
            <div className="h-80">
              {simulationData && simulationData.trade_history.length > 0 ? (
                <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#6b7280' } }, y: { ticks: { color: '#6b7280' } } } }} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                  {botStatus.is_running ? 'En attente de données de trading...' : 'Démarrez une session pour voir les performances.'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
