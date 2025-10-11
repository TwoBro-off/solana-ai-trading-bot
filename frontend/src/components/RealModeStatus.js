import React, { useState, useEffect } from 'react';

function StatusItem({ label, status, value, error }) {
    const isOk = status === 'ok';
    return (
        <div className={`flex justify-between items-center p-3 rounded-lg ${isOk ? 'bg-green-50' : 'bg-red-50'}`}>
            <div>
                <span className="font-medium text-gray-800">{label}</span>
                {value && <span className="ml-2 text-sm text-gray-600 font-mono">{value}</span>}
                {error && <p className="text-xs text-red-700 mt-1">{error}</p>}
            </div>
            <span className={`text-2xl ${isOk ? 'text-green-500' : 'text-red-500'}`}>
                {isOk ? '✅' : '❌'}
            </span>
        </div>
    );
}

function RealModeStatus() {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const response = await fetch('/api/pre-flight-check');
                if (!response.ok) {
                    throw new Error('Failed to fetch pre-flight status');
                }
                const data = await response.json();
                setStatus(data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 10000); // Refresh every 10 seconds
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return <div className="p-4 text-center">Vérification du mode réel en cours...</div>;
    }

    if (!status || status.simulation_mode) {
        return null; // Ne rien afficher si en mode simulation ou si les données ne sont pas chargées
    }

    return (
        <div className="p-6 bg-white rounded-lg shadow-md border-l-4 border-yellow-500 mb-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Pré-vérification pour le Mode Réel</h2>
            <div className="space-y-3">
                <StatusItem
                    label="Connexion du Wallet de Trading"
                    status={status.wallet.connected ? 'ok' : 'error'}
                    value={status.wallet.address ? `${status.wallet.address.substring(0, 6)}...` : null}
                    error={!status.wallet.connected ? 'Clé privée invalide ou non configurée dans .env' : null}
                />
                <StatusItem
                    label="Solde du Wallet de Trading"
                    status={status.wallet.balance_ok ? 'ok' : 'error'}
                    value={`${status.wallet.balance_sol.toFixed(4)} SOL`}
                    error={!status.wallet.balance_ok ? 'Solde insuffisant pour trader.' : null}
                />
                <StatusItem label="Connexion au Nœud RPC Solana" status={status.rpc_connection ? 'ok' : 'error'} />
                <StatusItem label="Connexion à l'API Jupiter" status={status.jupiter_api ? 'ok' : 'error'} />
            </div>
        </div>
    );
}

export default RealModeStatus;