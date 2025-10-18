import React, { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const OFFLINE_STATUS = { is_running: false, current_mode: 'Déconnecté', is_offline: true };

function LiveActivityPage() {
  // Initialize state with default objects to prevent null errors
  const [botStatus, setBotStatus] = useState(OFFLINE_STATUS);
  const [activityLog, setActivityLog] = useState([]);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/status`);
      if (!response.ok) throw new Error('Backend not responding');
      const data = await response.json();
      setBotStatus(data); // Set state
      return data; // Return data for sequential logic
    } catch (err) {
      setBotStatus(OFFLINE_STATUS);
      setError('Impossible de contacter le backend.');
      return null; // Return null on failure
    }
  }, [setBotStatus, setError]); // Dépendances sur les setters, qui sont stables.

  const fetchActivityLog = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/activity`);
      if (!response.ok) return;
      const data = await response.json();
      // Ensure data is always an array
      if (Array.isArray(data)) {
        setActivityLog(data);
      }
    } catch (err) { /* Fail silently */
      // Fail silently, the error message from status check is enough
    }
  }, []);

  useEffect(() => {
    const updateData = async () => {
      const status = await fetchBotStatus(); // Correctly await the promise
      if (isPageLoading) setIsPageLoading(false);

      if (status && status.is_running) {
        await fetchActivityLog();
      } else {
        setActivityLog([]); // Clear log if bot is not running
      }
    };

    updateData(); // Initial call
    const interval = setInterval(updateData, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [fetchBotStatus, fetchActivityLog, isPageLoading]);

  if (isPageLoading) {
    return <div className="text-center py-10">Chargement des activités...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Activité en Direct</h1>
      {error && <p className="text-red-500 bg-red-50 p-3 rounded-lg mb-4">{error}</p>}
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Journal d'Événements</h3>
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${botStatus?.is_running ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {botStatus?.is_running ? 'Actif' : 'Arrêté'}
            </span>
          </div>
        </div>
        <div className="border-t border-gray-200">
          {activityLog.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {activityLog.map((log, index) => (
                <li key={index} className="p-4 flex items-start space-x-3">
                  <div className={`flex-shrink-0 h-2.5 w-2.5 rounded-full mt-1.5 ${log.level === 'SUCCESS' ? 'bg-green-500' : log.level === 'ERROR' ? 'bg-red-500' : 'bg-sky-500'}`}></div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-800">{log.message}</p>
                    <p className="text-xs text-gray-500 mt-1">{new Date(log.timestamp * 1000).toLocaleString()}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-center py-12 px-6">
              <p className="text-gray-500">
                {botStatus?.is_running ? "En attente des premières activités..." : "Le bot est arrêté. Démarrez une session pour voir l'activité."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default LiveActivityPage;