
import React from 'react';
import { Navigate } from 'react-router-dom';

export default function PrivateRoute({ children }) {
  const isAuthenticated = localStorage.getItem('token');
  return isAuthenticated ? (
    <div className="app-container min-h-screen flex items-center justify-center">
      <div className="card w-full max-w-2xl">
        {children}
      </div>
    </div>
  ) : (
    <Navigate to="/login" />
  );
}