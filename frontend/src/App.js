import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Dashboard from './components/Dashboard.js';
import Settings from './components/Settings.js';
import Header from './Header.js';
import './App.css';

function App() {
  return (
    <Router>
      <div className="bg-gray-50 min-h-screen text-gray-800 font-sans">
        <Header />
        <main>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/" element={<Navigate to="/dashboard" />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;