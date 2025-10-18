import React, { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Settings({ botStatus }) {
  const [settings, setSettings] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [saveStatus, setSaveStatus] = useState({}); // Pour suivre le statut de sauvegarde par champ

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/env`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleInputChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async (key) => {
    setSaveStatus(prev => ({ ...prev, [key]: 'saving' }));
    try {
      const response = await fetch(`${API_URL}/api/env/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: settings[key] }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || 'Failed to save');
      setSaveStatus(prev => ({ ...prev, [key]: 'saved' }));
    } catch (err) {
      setSaveStatus(prev => ({ ...prev, [key]: 'error' }));
      console.error(`Failed to save ${key}:`, err);
    } finally {
      setTimeout(() => setSaveStatus(prev => ({ ...prev, [key]: null })), 2000);
    }
  };

  const renderInput = (key, label, type = 'text') => (
    <div key={key}>
      <label className="block text-sm font-medium text-gray-600">{label}</label>
      <div className="mt-1 flex rounded-md shadow-sm">
        <input
          type={type}
          value={settings[key] || ''}
          onChange={(e) => handleInputChange(key, e.target.value)}
          className="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-l-md focus:ring-sky-500 focus:border-sky-500 sm:text-sm border-gray-300"
          disabled={isLoading || botStatus.is_offline} // Les champs sont modifiables même si le bot tourne
        />
        <button
          onClick={() => handleSave(key)}
          disabled={isLoading || botStatus.is_offline || saveStatus[key] === 'saving'}
          className="inline-flex items-center px-3 rounded-r-md border border-l-0 border-gray-300 bg-gray-50 text-gray-500 text-sm disabled:opacity-50 hover:bg-gray-100"
        >
          {saveStatus[key] === 'saving' ? '...' : saveStatus[key] === 'saved' ? '✓' : saveStatus[key] === 'error' ? '✗' : 'Save'}
        </button>
      </div>
    </div>
  );

  if (isLoading) {
    return <div className="text-sm text-gray-500">Chargement des paramètres...</div>;
  }

  if (error) {
    return <div className="text-sm text-red-500">Erreur: {error}</div>;
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Stratégie & IA</h3>
      <div className="space-y-4">
        {renderInput('BUY_AMOUNT_SOL', 'Montant d\'achat (SOL)', 'number')}
        {renderInput('SELL_MULTIPLIER', 'Multiplicateur de vente (ex: 2.0 pour x2)', 'number')}
        {renderInput('TRAILING_STOP_PERCENT', 'Trailing Stop (ex: 0.15 pour 15%)', 'number')}
        <hr/>
        <h4 className="text-md font-medium text-gray-700 pt-2">Configuration IA</h4>
        {renderInput('GEMINI_MODEL', 'Modèle Gemini')}
        {renderInput('GEMINI_API_KEY_1', 'Clé API Gemini 1')}
        {renderInput('GEMINI_API_KEY_2', 'Clé API Gemini 2')}
        {renderInput('GEMINI_API_KEY_3', 'Clé API Gemini 3')}
      </div>
    </div>
  );
}

export default Settings;