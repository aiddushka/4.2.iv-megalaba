import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, setStoredToken } from "../api/authApi";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await login(username, password);
      setStoredToken(access_token);
      navigate("/dashboard", { replace: true });
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  const formStyle: React.CSSProperties = {
    maxWidth: 360,
    margin: "0 auto",
    padding: "2rem",
    background: "#020617",
    borderRadius: 16,
    border: "1px solid #1f2937",
  };
  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.6rem 0.75rem",
    borderRadius: 8,
    border: "1px solid #1f2937",
    background: "#0f172a",
    color: "#e5e7eb",
    fontSize: "0.95rem",
    marginBottom: "1rem",
    boxSizing: "border-box",
  };

  return (
    <div style={{ padding: "2rem" }}>
      <div style={formStyle}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1.5rem" }}>
          Вход
        </h2>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Логин"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={inputStyle}
            required
            autoComplete="username"
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
            required
            autoComplete="current-password"
          />
          {error && (
            <p style={{ color: "#fca5a5", fontSize: "0.9rem", marginBottom: "1rem" }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.6rem",
              borderRadius: 8,
              border: "none",
              background: loading ? "#4b5563" : "linear-gradient(90deg,#22c55e,#22d3ee)",
              color: "#020617",
              fontWeight: 600,
              cursor: loading ? "default" : "pointer",
              fontSize: "0.95rem",
            }}
          >
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>
        <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#9ca3af" }}>
          Нет аккаунта?{" "}
          <Link to="/register" style={{ color: "#67e8f9" }}>
            Регистрация
          </Link>
        </p>
      </div>
    </div>
  );
}
