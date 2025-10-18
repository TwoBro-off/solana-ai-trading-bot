import React, { useState } from "react";
import axios from "axios";

const AutoUpdate = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  const handleUpdate = async () => {
    setLoading(true);
    setResult("");
    setError("");
    try {
      const res = await axios.post("/api/auto_update");
      setResult(res.data.message || "Mise à jour réussie.");
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
    setLoading(false);
  };

  return (
    <div className="mb-4 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded">
      <div className="font-semibold mb-2">Mise à jour automatique du bot</div>
      <button
        className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
        onClick={handleUpdate}
        disabled={loading}
      >
        {loading ? "Mise à jour en cours..." : "Lancer la mise à jour"}
      </button>
      {result && <div className="text-green-700 mt-2 text-xs whitespace-pre-line">{result}</div>}
      {error && <div className="text-red-700 mt-2 text-xs whitespace-pre-line">{error}</div>}
    </div>
  );
};

export default AutoUpdate;
