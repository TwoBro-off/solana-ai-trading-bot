import React, { useEffect, useState } from "react";
import axios from "axios";

export default function GeminiSuggestions({ results }) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!results || !Array.isArray(results) || results.length === 0) return;
    setLoading(true);
    setError("");
    // Appel backend Gemini (exemple: /api/ai/gemini_suggestions)
    axios.post("/api/ai/gemini_suggestions", { results })
      .then(res => setSuggestions(res.data.suggestions || []))
      .catch(e => setError("Erreur Gemini: " + (e.response?.data?.detail || e.message)))
      .finally(() => setLoading(false));
  }, [results]);

  return (
    <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-purple-100 rounded border border-blue-200">
      <h4 className="font-semibold mb-2 text-blue-800">Suggestions IA Gemini</h4>
      {loading && <div className="text-blue-500">Analyse IA en cours...</div>}
      {error && <div className="text-red-500">{error}</div>}
      {suggestions.length > 0 && (
        <ul className="list-disc pl-6 text-sm text-blue-900">
          {suggestions.map((s, i) => <li key={i}>{s}</li>)}
        </ul>
      )}
      {!loading && !error && suggestions.length === 0 && <div className="text-gray-500 text-xs">Aucune suggestion IA pour l’instant.</div>}
    </div>
  );
}
