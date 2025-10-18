import React, { useEffect, useState } from "react";
import axios from "axios";

const AdvancedMonitoring = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let interval;
    const fetchMetrics = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await axios.get("/api/monitoring/metrics");
        setMetrics(res.data);
      } catch (err) {
        setError("Erreur de récupération des métriques : " + (err.response?.data?.detail || err.message));
      }
      setLoading(false);
    };
    fetchMetrics();
    interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="text-xs text-gray-500">Chargement des métriques...</div>;
  if (error) return <div className="text-xs text-red-500">{error}</div>;
  if (!metrics) return null;

  // Détection d'alertes
  const alert = metrics.global_status !== "OK" || metrics.cpu_usage > 85 || metrics.memory_usage > 8000 || metrics.critical_errors_24h > 0;
  return (
    <div className={`mb-4 p-4 border-l-4 rounded ${alert ? 'bg-red-100 border-red-500' : 'bg-gray-100 border-blue-400'}`}>
      <div className="font-semibold mb-2 flex items-center">
        Monitoring avancé du bot
        {alert && <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded">ALERTE</span>}
      </div>
      <ul className="text-xs grid grid-cols-2 md:grid-cols-4 gap-2">
        <li>Trades en temps réel : <span className="font-bold text-blue-700">{metrics.trades_last_minute}</span></li>
        <li>Latence API (ms) : <span className="font-bold text-blue-700">{metrics.api_latency}</span></li>
        <li>Solde TrustWallet : <span className="font-bold text-green-700">{metrics.wallet_balance} SOL</span></li>
        <li>CPU (%) : <span className={`font-bold ${metrics.cpu_usage > 85 ? 'text-red-700' : 'text-purple-700'}`}>{metrics.cpu_usage}</span></li>
        <li>Mémoire (MB) : <span className={`font-bold ${metrics.memory_usage > 8000 ? 'text-red-700' : 'text-purple-700'}`}>{metrics.memory_usage}</span></li>
        <li>Nombre de tokens surveillés : <span className="font-bold text-blue-700">{metrics.tokens_watched}</span></li>
        <li>Erreurs critiques (24h) : <span className={`font-bold ${metrics.critical_errors_24h > 0 ? 'text-red-700' : 'text-green-700'}`}>{metrics.critical_errors_24h}</span></li>
        <li>Uptime bot : <span className="font-bold text-green-700">{metrics.uptime}</span></li>
      </ul>
      <div className="mt-4">
        <div className="font-semibold text-xs mb-1">État des modules critiques :</div>
        <ul className="text-xs grid grid-cols-2 md:grid-cols-3 gap-2">
          {metrics.modules_status && Object.entries(metrics.modules_status).map(([k, v]) => (
            k !== "global" && <li key={k}>{k} : <span className={`font-bold ${v === 'OK' ? 'text-green-700' : v === 'Non configuré' ? 'text-gray-500' : 'text-red-700'}`}>{v}</span></li>
          ))}
        </ul>
        <div className="mt-2 text-xs">Statut global : <span className={`font-bold ${metrics.global_status === 'OK' ? 'text-green-700' : 'text-red-700'}`}>{metrics.global_status}</span></div>
      </div>
    </div>
  );
};

export default AdvancedMonitoring;
