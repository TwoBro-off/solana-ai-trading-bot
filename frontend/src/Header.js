import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';

const API_URL = process.env.REACT_APP_API_URL;

function Header() {
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/bot/status`);
        setIsBackendOnline(response.ok);
      } catch (error) {
        setIsBackendOnline(false);
      }
    };

    const interval = setInterval(checkBackendStatus, 10000); // Check every 10 seconds
    checkBackendStatus(); // Initial check
    return () => clearInterval(interval);
  }, []);

  const activeLinkStyle = {
    color: '#0c4a6e', // sky-900
    backgroundColor: '#e0f2fe', // sky-100
  };

  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200/80 sticky top-0 z-50">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-6">
            <div className="flex-shrink-0 flex items-center space-x-2">
              <img className="h-8 w-auto" src="/logo192.png" alt="AlphaStriker Logo" />
              <span className="text-xl font-bold text-gray-900 tracking-tight">AlphaStriker</span>
            </div>
            <div className="hidden md:flex md:space-x-2">
              <NavLink to="/" end style={({ isActive }) => isActive ? activeLinkStyle : undefined} className="text-gray-500 hover:bg-gray-100 hover:text-gray-800 px-3 py-2 rounded-md text-sm font-medium transition-colors">Tableau de Bord</NavLink>
              <NavLink to="/activity" style={({ isActive }) => isActive ? activeLinkStyle : undefined} className="text-gray-500 hover:bg-gray-100 hover:text-gray-800 px-3 py-2 rounded-md text-sm font-medium transition-colors">Activité en Direct</NavLink>
              <NavLink to="/strategy" style={({ isActive }) => isActive ? activeLinkStyle : undefined} className="text-gray-500 hover:bg-gray-100 hover:text-gray-800 px-3 py-2 rounded-md text-sm font-medium transition-colors">Stratégie & IA</NavLink>
              <NavLink to="/ai-analysis" style={({ isActive }) => isActive ? activeLinkStyle : undefined} className="text-gray-500 hover:bg-gray-100 hover:text-gray-800 px-3 py-2 rounded-md text-sm font-medium transition-colors">Analyse IA</NavLink>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`h-2.5 w-2.5 rounded-full ${isBackendOnline ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-500">{isBackendOnline ? 'Connecté' : 'Déconnecté'}</span>
          </div>
        </div>
      </nav>
    </header>
  );
}

export default Header;