import React, { useState, useEffect } from 'react';
import { WinrateHistoryChart } from './BacktestCharts';

function AIStatusPanel() {
    const [status, setStatus] = useState(null);
    const [history, setHistory] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await fetch('/api/ai/optimizer/status');
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to fetch AI status');
                }
                const result = await response.json();
                setStatus(result);
                setError(null);
            } catch (err) {
                setError(err.message);
            }
        };

        const fetchHistory = async () => {
            try {
                const response = await fetch('/api/ai/optimizer/history');
                if (!response.ok) {
                    throw new Error('Failed to fetch AI history');
                }
                const result = await response.json();
                setHistory(result);
            } catch (err) {
                // Ne pas afficher d'erreur critique si seul l'historique échoue
                console.error(err.message);
            }
        };

        fetchStatus();
        fetchHistory();
        const interval = setInterval(fetchStatus, 5000); // Refresh every 5 seconds

        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (
            <div className="bg-white p-5 rounded-lg shadow">
                <h2 className="text-xl font-semibold text-gray-700 mb-2">Statut de l'Optimiseur IA</h2>
                <p className="text-red-500">Erreur de chargement: {error}</p>
            </div>
        );
    }

    if (!status) {
        return (
            <div className="bg-white p-5 rounded-lg shadow">
                <h2 className="text-xl font-semibold text-gray-700 mb-2">Statut de l'Optimiseur IA</h2>
                <p>Chargement...</p>
            </div>
        );
    }

    return (
        <div className="bg-white p-5 rounded-lg shadow">
            <h2 className="text-xl font-semibold text-gray-700 mb-4">Statut de l'Optimiseur IA</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                    <p className="text-sm text-gray-500">Profil Stratégie</p>
                    <p className="text-lg font-bold text-blue-600 capitalize">{status.current_profile_name}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">Winrate</p>
                    <p className="text-lg font-semibold">{(status.winrate * 100).toFixed(1)}%</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">Max Drawdown</p>
                    <p className="text-lg font-semibold">{(status.max_drawdown * 100).toFixed(1)}%</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">État</p>
                    <p className={`text-lg font-bold ${status.freeze ? 'text-green-600' : 'text-yellow-600'}`}>{status.freeze ? 'Stable (Freeze)' : 'Optimisation'}</p>
                </div>
            </div>
            <div className="mt-6">
                <h3 className="text-md font-semibold text-gray-600 mb-2">Évolution du Winrate</h3>
                <WinrateHistoryChart history={history} />
            </div>
        </div>
    );
}

export default AIStatusPanel;