import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './Header.js';
import Dashboard from './components/Dashboard.js';
import SettingsPage from './SettingsPage.js';
import LiveActivityPage from './LiveActivityPage.js';
import AIAnalysisPage from './AIAnalysisPage.js';
import ErrorBoundary from './components/ErrorBoundary.js';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Header />
        <main className="bg-gray-50 min-h-[calc(100vh-4rem)]">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/strategy" element={<SettingsPage />} />
            <Route path="/activity" element={<LiveActivityPage />} />
            <Route path="/ai-analysis" element={<AIAnalysisPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </Router>
    </ErrorBoundary>
  );
}

export default App;