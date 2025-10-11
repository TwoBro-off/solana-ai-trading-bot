import React from "react";
import { Line, Bar } from "react-chartjs-2";
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend } from "chart.js";

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend);

export function PnLChart({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) return null;
  let cumPnL = 0;
  const labels = results.map((r, i) => `Run ${i + 1}`);
  const data = results.map(r => {
    cumPnL += r.performance?.total_profit || 0;
    return cumPnL;
  });
  return (
    <div className="mb-4">
      <h4 className="font-semibold mb-1">Courbe PnL cumulée</h4>
      <Line data={{
        labels,
        datasets: [{
          label: "PnL cumulé",
          data,
          fill: false,
          borderColor: "#2563eb",
          backgroundColor: "#60a5fa",
          tension: 0.2
        }]
      }} options={{ responsive: true, plugins: { legend: { display: false } } }} height={120} />
    </div>
  );
}

export function DrawdownChart({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) return null;
  let maxPnL = 0, pnl = 0;
  const drawdowns = results.map(r => {
    pnl += r.performance?.total_profit || 0;
    if (pnl > maxPnL) maxPnL = pnl;
    return maxPnL - pnl;
  });
  return (
    <div className="mb-4">
      <h4 className="font-semibold mb-1">Drawdown par run</h4>
      <Bar data={{
        labels: results.map((_, i) => `Run ${i + 1}`),
        datasets: [{
          label: "Drawdown",
          data: drawdowns,
          backgroundColor: "#f87171"
        }]
      }} options={{ responsive: true, plugins: { legend: { display: false } } }} height={120} />
    </div>
  );
}

export function TradesHeatmap({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) return null;
  // Simple heatmap: nombre de trades par run
  const tradeCounts = results.map(r => r.trades?.length || 0);
  return (
    <div className="mb-4">
      <h4 className="font-semibold mb-1">Heatmap : nombre de trades par run</h4>
      <Bar data={{
        labels: results.map((_, i) => `Run ${i + 1}`),
        datasets: [{
          label: "# Trades",
          data: tradeCounts,
          backgroundColor: "#34d399"
        }]
      }} options={{ responsive: true, plugins: { legend: { display: false } } }} height={120} />
    </div>
  );
}

export function SimulationPnLChart({ tradeHistory }) {
  if (!tradeHistory || !Array.isArray(tradeHistory) || tradeHistory.length === 0) {
    return <p className="text-center text-gray-500">Pas de données de trade pour afficher le graphique.</p>;
  }

  const labels = [];
  const pnlData = [];
  let cumulativePnl = 0;
  const buyPrices = {};

  tradeHistory.forEach((trade, index) => {
    if (trade.action === 'buy') {
      buyPrices[trade.token] = trade.price;
    } else if (trade.action === 'sell' && buyPrices[trade.token] !== undefined) {
      const profit = trade.price - buyPrices[trade.token];
      cumulativePnl += profit;
      labels.push(`Trade #${index + 1}`);
      pnlData.push(cumulativePnl);
      // On pourrait supprimer buyPrices[trade.token] si un token ne peut être acheté qu'une fois
    }
  });

  const chartData = {
    labels,
    datasets: [{
      label: 'PnL Cumulé (SOL)',
      data: pnlData,
      fill: true,
      backgroundColor: 'rgba(37, 99, 235, 0.2)',
      borderColor: 'rgba(37, 99, 235, 1)',
      tension: 0.1,
      pointRadius: 2,
    }]
  };

  return <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false }} height={250} />;
}

export function WinrateHistoryChart({ history }) {
  if (!history || !Array.isArray(history) || history.length === 0) {
    return <p className="text-center text-gray-500 text-sm py-4">Pas assez de données pour afficher l'historique du winrate.</p>;
  }

  const labels = history.map(h => new Date(h.timestamp * 1000).toLocaleTimeString());
  const winrateData = history.map(h => h.winrate * 100);

  const chartData = {
    labels,
    datasets: [{
      label: 'Winrate (%)',
      data: winrateData,
      fill: false,
      backgroundColor: 'rgba(22, 163, 74, 0.2)',
      borderColor: 'rgba(22, 163, 74, 1)',
      tension: 0.2,
      pointRadius: 1,
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 100 }
    }
  };

  return <Line data={chartData} options={options} height={150} />;
}
