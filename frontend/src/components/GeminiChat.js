import React, { useState } from 'react';

const GeminiChat = () => {
  const [messages, setMessages] = useState([
    { role: 'system', content: "Bienvenue ! Posez une question ou demandez une modification du bot. L'IA Gemini (OpenRouter) répondra et pourra agir sur le code si autorisé." }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    setLoading(true);
    const userMsg = { role: 'user', content: input };
    setMessages(msgs => [...msgs, userMsg]);
    setInput('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/gemini-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: input })
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(msgs => [...msgs, { role: 'assistant', content: data.reply }]);
      } else {
        setMessages(msgs => [...msgs, { role: 'assistant', content: "Erreur lors de la réponse de l'IA." }]);
      }
    } catch {
      setMessages(msgs => [...msgs, { role: 'assistant', content: "Erreur réseau ou serveur inaccessible." }]);
    }
    setLoading(false);
  };

  return (
    <div className="app-container flex items-center justify-center min-h-screen bg-gray-50">
      <div className="card w-full max-w-2xl">
        <h2 className="text-xl font-bold mb-4 text-blue-600">Gemini Chat (OpenRouter)</h2>
        <div className="mb-4 h-64 overflow-y-auto bg-gray-50 rounded p-4 border border-gray-100">
          {messages.map((msg, idx) => (
            <div key={idx} className={`mb-2 text-sm ${msg.role === "user" ? "text-right text-blue-600" : msg.role === "assistant" ? "text-left text-gray-700" : "text-center text-gray-400"}`}>
              <span className="font-semibold">{msg.role === 'user' ? 'Vous' : msg.role === 'assistant' ? 'Gemini' : ''}:</span> {msg.content}
            </div>
          ))}
          {loading && <div className="text-left text-gray-400">Gemini réfléchit...</div>}
        </div>
        <form onSubmit={e => { e.preventDefault(); sendMessage(); }} className="flex gap-2">
          <input
            type="text"
            placeholder="Demandez une analyse, une modif, etc."
            value={input}
            onChange={e => setInput(e.target.value)}
            className="flex-1"
            disabled={loading}
          />
          <button type="submit" className="btn" disabled={loading}>{loading ? "..." : "Envoyer"}</button>
        </form>
      </div>
    </div>
  );
};

export default GeminiChat;
