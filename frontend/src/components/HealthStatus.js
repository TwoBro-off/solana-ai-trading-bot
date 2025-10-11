import React, { useEffect, useState } from "react";
import axios from "axios";

const HealthStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await axios.get("/api/healthcheck");
        setStatus(res.data);
      } catch (err) {
        setError("Impossible de vérifier l'état du bot : " + (err.response?.data?.detail || err.message));
      }
      setLoading(false);
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="text-xs text-gray-500">Vérification de l'état du bot...</div>;
  if (error) return <div className="text-xs text-red-500">{error}</div>;
  if (!status) return null;

  return (
    <div className="mb-4 p-3 bg-gray-50 border-l-4 border-gray-400 rounded">
      <div className="font-semibold mb-1">État global du bot : <span className={status.global === "OK" ? "text-green-700" : "text-red-700"}>{status.global}</span></div>
      <ul className="text-xs">
        <li>Paramètres utilisateur : <span className={status.user_settings === "OK" ? "text-green-700" : "text-red-700"}>{status.user_settings}</span></li>
        <li>Connexion Solana : <span className={status.solana_rpc === "OK" ? "text-green-700" : "text-red-700"}>{status.solana_rpc}</span></li>
        <li>IA Gemini : <span className={status.gemini_ai === "OK" ? "text-green-700" : "text-red-700"}>{status.gemini_ai}</span></li>
        <li>Backup GitHub : <span className={status.github_backup === "OK" ? "text-green-700" : "text-red-700"}>{status.github_backup}</span></li>
        <li>Base de réputation : <span className={status.reputation_db === "OK" ? "text-green-700" : "text-red-700"}>{status.reputation_db}</span></li>
      </ul>
    </div>
  );
};

export default HealthStatus;
