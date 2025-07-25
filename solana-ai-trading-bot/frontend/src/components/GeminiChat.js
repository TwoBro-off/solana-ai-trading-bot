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
    <div className="bg-gray-900 rounded-lg p-4 max-w-xl mx-auto mt-8 shadow-lg">
      <h2 className="text-xl font-bold mb-2 text-blue-300">Chat IA Gemini (OpenRouter)</h2>
      <div className="h-64 overflow-y-auto bg-gray-800 rounded p-2 mb-2 text-sm">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'text-right text-blue-200 mb-1' : 'text-left text-green-200 mb-1'}>
            <span className="font-semibold">{msg.role === 'user' ? 'Vous' : 'Gemini'}:</span> {msg.content}
          </div>
        ))}
        {loading && <div className="text-left text-gray-400">Gemini réfléchit...</div>}
      </div>
      <div className="flex">
        <input
          className="flex-1 rounded-l bg-gray-700 text-white px-3 py-2 focus:outline-none"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Demandez une analyse, une modif, etc."
          disabled={loading}
        />
        <button
          className="rounded-r bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 font-bold"
          onClick={sendMessage}
          disabled={loading}
        >Envoyer</button>
      </div>
    </div>
  );
};

export default GeminiChat;
