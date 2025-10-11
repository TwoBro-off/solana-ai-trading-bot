import React from "react";

export default function SecurityAlerts({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) return null;
  // Agrège toutes les alertes de sécurité trouvées dans les résultats
  const alerts = [];
  results.forEach((r, i) => {
    if (r.performance?.security_alerts && Array.isArray(r.performance.security_alerts)) {
      r.performance.security_alerts.forEach(a => alerts.push({ run: i + 1, ...a }));
    }
    // Legacy: certains runs peuvent avoir un champ 'alerts' ou 'anomalies'
    if (r.performance?.alerts && Array.isArray(r.performance.alerts)) {
      r.performance.alerts.forEach(a => alerts.push({ run: i + 1, ...a }));
    }
    if (r.performance?.anomalies && Array.isArray(r.performance.anomalies)) {
      r.performance.anomalies.forEach(a => alerts.push({ run: i + 1, ...a }));
    }
  });
  if (alerts.length === 0) return null;
  return (
    <div className="mb-4 p-4 bg-gradient-to-r from-red-50 to-yellow-100 rounded border border-red-200">
      <h4 className="font-semibold mb-2 text-red-800">Alertes Sécurité détectées</h4>
      <ul className="list-disc pl-6 text-sm text-red-900">
        {alerts.map((a, i) => (
          <li key={i}>
            <span className="font-bold">Run {a.run} :</span> {a.type ? `[${a.type}] ` : ''}{a.message || a.detail || JSON.stringify(a)}
          </li>
        ))}
      </ul>
    </div>
  );
}
