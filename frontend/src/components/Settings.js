import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Settings() {
  const [settings, setSettings] = useState({
    buy_amount_sol: 0.01,
    sell_multiplier: 2.0,
    trailing_stop_percent: 0.15,
    OPENROUTER_API_KEY: '',
    OPENROUTER_MODEL: 'google/gemini-flash-1.5',
  });
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch(`${API_URL}/api/env`);
        if (!response.ok) throw new Error('Failed to fetch settings');
        const envData = await response.json();
        
        setSettings(prev => ({
          ...prev,
          buy_amount_sol: parseFloat(envData.BUY_AMOUNT_SOL) || 0.01,
          sell_multiplier: parseFloat(envData.SELL_MULTIPLIER) || 2.0,
          trailing_stop_percent: parseFloat(envData.TRAILING_STOP_PERCENT) || 0.15,
          OPENROUTER_API_KEY: '********', // Masquer la clé par défaut
          OPENROUTER_MODEL: envData.OPENROUTER_MODEL || 'google/gemini-flash-1.5',
        }));
      } catch (err) {
        setError('Failed to load settings.');
        console.error(err);
      } finally {
        setIsPageLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      for (const [key, value] of Object.entries(settings)) {
        // Ne pas envoyer la clé API si elle n'a pas été changée
        if (key === 'OPENROUTER_API_KEY' && value.includes('*')) continue;

        await fetch(`${API_URL}/api/env/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: key.toUpperCase(), value: String(value) }),
        });
      }
      setSuccess('Paramètres sauvegardés avec succès !');
    } catch (err) {
      setError('Échec de la sauvegarde des paramètres. Le backend est-il accessible ?');
    }
  };

  if (isPageLoading) {
    return <div className="flex items-center justify-center h-[calc(100vh-4rem)]"><p className="text-gray-500">Chargement des paramètres...</p></div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h2 className="text-2xl font-bold tracking-tight text-gray-900 mb-8">Paramètres</h2>
      <form onSubmit={handleSubmit} className="max-w-3xl space-y-8">
        
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Stratégie de Trading</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {/* Buy Amount */}
            <div>
              <label htmlFor="buy_amount_sol" className="block text-sm font-medium text-gray-700">Montant d'achat</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <input type="number" name="buy_amount_sol" id="buy_amount_sol" value={settings.buy_amount_sol} onChange={(e) => setSettings(prev => ({...prev, buy_amount_sol: e.target.value}))} step="0.001" className="block w-full bg-gray-50/70 border-gray-300 rounded-md py-2 pl-3 pr-10 text-gray-900 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm" />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"><span className="text-gray-500 sm:text-sm">SOL</span></div>
              </div>
            </div>
            {/* Sell Multiplier */}
            <div>
              <label htmlFor="sell_multiplier" className="block text-sm font-medium text-gray-700">Objectif de Vente (x)</label>
              <input type="number" name="sell_multiplier" id="sell_multiplier" value={settings.sell_multiplier} onChange={(e) => setSettings(prev => ({...prev, sell_multiplier: e.target.value}))} step="0.1" className="mt-1 block w-full bg-gray-50/70 border-gray-300 rounded-md py-2 px-3 text-gray-900 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm" />
            </div>
            {/* Trailing Stop */}
            <div>
              <label htmlFor="trailing_stop_percent" className="block text-sm font-medium text-gray-700">Trailing Stop</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <input type="number" name="trailing_stop_percent" id="trailing_stop_percent" value={settings.trailing_stop_percent * 100} onChange={(e) => setSettings(prev => ({...prev, trailing_stop_percent: parseFloat(e.target.value) / 100}))} step="1" className="block w-full bg-gray-50/70 border-gray-300 rounded-md py-2 pl-3 pr-7 text-gray-900 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm" />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"><span className="text-gray-500 sm:text-sm">%</span></div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration IA</h3>
          <div className="space-y-4">
            <div>
              <label htmlFor="OPENROUTER_API_KEY" className="block text-sm font-medium text-gray-700">Clé API OpenRouter</label>
              <input type="password" name="OPENROUTER_API_KEY" id="OPENROUTER_API_KEY" value={settings.OPENROUTER_API_KEY} onChange={(e) => setSettings(prev => ({...prev, OPENROUTER_API_KEY: e.target.value}))} placeholder="Laisser vide pour ne pas changer" className="mt-1 block w-full bg-gray-50/70 border-gray-300 rounded-md py-2 px-3 text-gray-900 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm" />
            </div>
            <div>
              <label htmlFor="OPENROUTER_MODEL" className="block text-sm font-medium text-gray-700">Modèle IA (OpenRouter)</label>
              <input type="text" name="OPENROUTER_MODEL" id="OPENROUTER_MODEL" value={settings.OPENROUTER_MODEL} onChange={(e) => setSettings(prev => ({...prev, OPENROUTER_MODEL: e.target.value}))} className="mt-1 block w-full bg-gray-50/70 border-gray-300 rounded-md py-2 px-3 text-gray-900 focus:outline-none focus:ring-sky-500 focus:border-sky-500 sm:text-sm" />
            </div>
          </div>
        </div>

        <div className="flex justify-end items-center space-x-4 pt-4">
          {success && <p className="text-sm text-green-600">{success}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2 px-5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-50 focus:ring-sky-500">
            Sauvegarder
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;