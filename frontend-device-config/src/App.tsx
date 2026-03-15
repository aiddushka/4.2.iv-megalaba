import { Route, Routes } from "react-router-dom";
import { RegisterDevicePage } from "./pages/RegisterDevicePage";

export default function App() {
  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#e5e7eb" }}>
      <header
        style={{
          padding: "1rem 2rem",
          borderBottom: "1px solid #1f2937",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Device Configurator</h1>
      </header>
      <main style={{ padding: "2rem" }}>
        <Routes>
          <Route path="/" element={<RegisterDevicePage />} />
        </Routes>
      </main>
    </div>
  );
}

