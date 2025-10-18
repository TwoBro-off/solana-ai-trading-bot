import React from 'react';
import Settings from './components/Settings.js';

function SettingsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="space-y-8">
        <h1 className="text-2xl font-bold text-gray-800">Stratégie & Configuration IA</h1>
        <Settings botStatus={{}} /> {/* Passe un statut neutre car la page est indépendante */}
      </div>
    </div>
  );
}

export default SettingsPage;