import React, { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function AIAnalysisPage() {
  const [aiStatus, setAiStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAIStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/ai/status`);
      if (response.ok) {
        const data = await response.json();
        setAiStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch AI status:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAIStatus();
    const interval = setInterval(fetchAIStatus, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [fetchAIStatus]);

  if (isLoading) {
    return <div className="text-center py-20 text-gray-500">Chargement des données de l'IA...</div>;
  }

  if (!aiStatus || !aiStatus.is_running) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <h1 className="text-2xl font-bold text-gray-800 mb-8">Analyse IA</h1>
        <div className="text-center py-20 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">Le module d'analyse IA est inactif.</p>
          <p className="text-gray-400 text-sm">Démarrez une session en mode simulation pour activer l'optimisation automatique.</p>
        </div>
      </div>
    );
  }

  const { last_analysis, decision_history, hall_of_fame } = aiStatus;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h1 className="text-2xl font-bold text-gray-800 mb-8">Centre de Commandement IA</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Colonne de gauche: Suggestions IA */}
        <div className="lg:col-span-1 space-y-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Dernière Analyse Gemini</h3>
            {last_analysis && last_analysis.parsed ? (
              <div className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-gray-700">Résumé</h4>
                  <p className="text-gray-600 italic">"{last_analysis.parsed.summary}"</p>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-700">Suggestions d'Action</h4>
                  <ul className="list-disc list-inside text-gray-600 space-y-1 mt-1">
                    {last_analysis.parsed.actionable_suggestions?.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-700">Problèmes Potentiels</h4>
                  <ul className="list-disc list-inside text-gray-600 space-y-1 mt-1">
                    {last_analysis.parsed.potential_issues?.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">En attente de la première analyse des logs de trading...</p>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hall of Fame des Stratégies</h3>
            <p className="text-xs text-gray-500 mb-3">Meilleures combinaisons de paramètres découvertes par l'IA.</p>
            <table className="min-w-full text-sm">
              <thead className="text-left text-gray-500"><tr><th className="p-2">Achat (SOL)</th><th className="p-2">Vente (x)</th></tr></thead>
              <tbody className="divide-y divide-gray-200">
                {hall_of_fame?.map((params, i) => (
                  <tr key={i}><td className="p-2 font-mono">{params.buy_amount_sol.toFixed(4)}</td><td className="p-2 font-mono">{params.sell_multiplier.toFixed(2)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Colonne de droite: Historique des décisions */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Historique des Décisions de l'IA</h3>
            <div className="overflow-y-auto h-[70vh] space-y-4 pr-2">
              {decision_history?.length > 0 ? decision_history.map((d, i) => (
                <div key={i} className="text-xs p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-sky-700">{d.action.replace(/_/g, ' ').toUpperCase()}</span>
                    <span className="text-gray-400">{new Date(d.timestamp * 1000).toLocaleString()}</span>
                  </div>
                  <p className="text-gray-600 italic mb-2">Raison: {d.reason}</p>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div><div className="text-gray-500">Anciens Param.</div><div className="font-mono bg-red-50 text-red-700 rounded px-1">{d.details.old_params.buy_amount_sol?.toFixed(4)} / {d.details.old_params.sell_multiplier?.toFixed(2)}x</div></div>
                    <div><div className="text-gray-500">Nouveaux Param.</div><div className="font-mono bg-green-50 text-green-700 rounded px-1">{d.details.new_params.buy_amount_sol?.toFixed(4)} / {d.details.new_params.sell_multiplier?.toFixed(2)}x</div></div>
                  </div>
                </div>
              )).reverse() : <p className="text-sm text-gray-500 text-center pt-10">Aucune décision d'ajustement prise pour le moment.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIAnalysisPage;