import { useEffect, useState } from "react";
import { Route, Routes, NavLink, useNavigate } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { UnassignedDevicesPage } from "./pages/UnassignedDevicesPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { WorkersPage } from "./pages/WorkersPage";
import { getStoredToken, getMe, clearStoredToken } from "./api/authApi";
import type { User } from "./api/authApi";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }
    getMe()
      .then((u) => {
        setUser(u);
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setAuthLoading(false);
      });
  }, []);

  const linkStyle: React.CSSProperties = {
    color: "#9ca3af",
    textDecoration: "none",
    padding: "0.25rem 0.75rem",
    borderRadius: 999,
    fontSize: "0.85rem",
  };

  const activeStyle: React.CSSProperties = {
    ...linkStyle,
    background: "rgba(34,197,94,0.1)",
    color: "#bbf7d0",
  };

  const handleLogout = () => {
    clearStoredToken();
    setUser(null);
    navigate("/login", { replace: true });
  };

  if (authLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#020617",
          color: "#e5e7eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Загрузка...
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ minHeight: "100vh", background: "#020617", color: "#e5e7eb" }}>
        <header
          style={{
            padding: "1rem 2rem",
            borderBottom: "1px solid #1f2937",
          }}
        >
          <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Greenhouse</h1>
        </header>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </div>
    );
  }

  const isAdmin = user.is_admin;
  const canViewDashboard = isAdmin || user.can_view_dashboard;

  // Работник без права на дашборд — только страница «доступ запрещён»
  if (!canViewDashboard) {
    return (
      <div style={{ minHeight: "100vh", background: "#020617", color: "#e5e7eb" }}>
        <header
          style={{
            padding: "1rem 2rem",
            borderBottom: "1px solid #1f2937",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Greenhouse Dashboard</h1>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ fontSize: "0.85rem", color: "#9ca3af" }}>
              {user.username} (работник)
            </span>
            <button
              type="button"
              onClick={handleLogout}
              style={{
                padding: "0.25rem 0.75rem",
                borderRadius: 999,
                border: "1px solid #374151",
                background: "transparent",
                color: "#9ca3af",
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              Выход
            </button>
          </div>
        </header>
        <main style={{ padding: "2rem", textAlign: "center" }}>
          <p style={{ fontSize: "1.1rem", color: "#9ca3af", marginBottom: "0.5rem" }}>
            Доступ к дашборду запрещён
          </p>
          <p style={{ fontSize: "0.9rem", color: "#6b7280" }}>
            Обратитесь к администратору для получения прав на просмотр.
          </p>
        </main>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#020617", color: "#e5e7eb" }}>
      <header
        style={{
          padding: "1rem 2rem",
          borderBottom: "1px solid #1f2937",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Greenhouse Dashboard</h1>
        <nav style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <NavLink
            to="/"
            style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
            end
          >
            Доска
          </NavLink>
          {isAdmin && (
            <NavLink
              to="/unassigned"
              style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
            >
              Неустановленные устройства
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/workers"
              style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
            >
              Работники
            </NavLink>
          )}
          <span style={{ fontSize: "0.85rem", color: "#9ca3af", marginLeft: "0.5rem" }}>
            {user.username}
            {isAdmin ? " (админ)" : " (работник)"}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            style={{
              padding: "0.25rem 0.75rem",
              borderRadius: 999,
              border: "1px solid #374151",
              background: "transparent",
              color: "#9ca3af",
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            Выход
          </button>
        </nav>
      </header>
      <main style={{ padding: "2rem" }}>
        <Routes>
          <Route path="/" element={<DashboardPage isAdmin={isAdmin} />} />
          <Route path="/unassigned" element={<UnassignedDevicesPage />} />
          <Route path="/workers" element={<WorkersPage />} />
        </Routes>
      </main>
    </div>
  );
}
