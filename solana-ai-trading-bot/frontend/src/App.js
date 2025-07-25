import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import PrivateRoute from './components/PrivateRoute';
import GeminiChat from './components/GeminiChat';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route path="/chat" element={<PrivateRoute><GeminiChat /></PrivateRoute>} />
          <Route path="*" element={<Login />} /> {/* Default to login page */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;