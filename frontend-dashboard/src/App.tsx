import { Route, Routes, NavLink } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { UnassignedDevicesPage } from "./pages/UnassignedDevicesPage";

export default function App() {
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
        <nav style={{ display: "flex", gap: "0.5rem" }}>
          <NavLink
            to="/"
            style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
            end
          >
            Доска
          </NavLink>
          <NavLink
            to="/unassigned"
            style={({ isActive }) => (isActive ? activeStyle : linkStyle)}
          >
            Неустановленные устройства
          </NavLink>
        </nav>
      </header>
      <main style={{ padding: "2rem" }}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/unassigned" element={<UnassignedDevicesPage />} />
        </Routes>
      </main>
    </div>
  );
}

