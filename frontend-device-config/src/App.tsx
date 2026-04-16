import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { RegisterDevicePage } from "./pages/RegisterDevicePage";
import { RemoveDevicePage } from "./pages/RemoveDevicePage";

export default function App() {
  const location = useLocation();
  const isRemovePage = location.pathname.startsWith("/remove");

  const switchLinkStyle: React.CSSProperties = {
    color: "#bbf7d0",
    textDecoration: "none",
    padding: "0.35rem 0.9rem",
    borderRadius: 999,
    fontSize: "0.9rem",
    border: "1px solid #14532d",
    background: "rgba(34,197,94,0.12)",
    fontWeight: 600,
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#e5e7eb" }}>
      <header
        style={{
          padding: "1rem 2rem",
          borderBottom: "1px solid #1f2937",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div style={{ width: 220, color: "#9ca3af", fontSize: "0.9rem" }}>Greenhouse</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "0.75rem" }}>
          <div style={{ fontSize: "1rem", fontWeight: 600 }}>
            {isRemovePage ? "Удаление устройства" : "Добавление устройства"}
          </div>
          <Link to={isRemovePage ? "/add" : "/remove"} style={switchLinkStyle}>
            {isRemovePage ? "Добавление" : "Удаление"}
          </Link>
        </div>
        <div style={{ width: 220, textAlign: "right", fontSize: "0.85rem", color: "#6b7280" }}>
          :3001
        </div>
      </header>
      <main style={{ padding: "2rem" }}>
        <Routes>
          <Route path="/" element={<Navigate to="/add" replace />} />
          <Route path="/add" element={<RegisterDevicePage />} />
          <Route path="/remove" element={<RemoveDevicePage />} />
          <Route path="*" element={<Navigate to="/add" replace />} />
        </Routes>
      </main>
    </div>
  );
}

