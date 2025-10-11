import React, { useState } from "react";

export default function Register() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (password !== confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    try {
      const res = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      if (res.ok) {
        setSuccess("Inscription réussie ! Vous pouvez vous connecter.");
        setUsername(""); setPassword(""); setConfirm("");
      } else {
        const data = await res.json();
        setError(data.detail || "Erreur lors de l'inscription.");
      }
    } catch {
      setError("Erreur réseau ou serveur inaccessible.");
    }
  };

  return (
    <div className="app-container flex items-center justify-center min-h-screen">
      <div className="card w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-blue-600 text-center">Inscription</h2>
        <form onSubmit={handleRegister}>
          <input
            type="text"
            placeholder="Nom d'utilisateur"
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full mb-2"
            required
          />
          <input
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full mb-2"
            required
          />
          <input
            type="password"
            placeholder="Confirmer le mot de passe"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            className="w-full mb-2"
            required
          />
          {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
          {success && <p className="text-green-500 text-xs italic mb-4">{success}</p>}
          <button type="submit" className="w-full mt-4 btn">S'inscrire</button>
        </form>
      </div>
    </div>
  );
}
