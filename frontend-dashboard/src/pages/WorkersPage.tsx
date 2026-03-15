import { useEffect, useState } from "react";
import { fetchWorkers, setDashboardAccess, Worker } from "../api/workersApi";

export function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWorkers();
      setWorkers(data);
    } catch {
      setError("Не удалось загрузить список работников");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleToggle = async (w: Worker) => {
    setUpdatingId(w.id);
    try {
      const updated = await setDashboardAccess(w.id, !w.can_view_dashboard);
      setWorkers((prev) =>
        prev.map((x) => (x.id === updated.id ? updated : x))
      );
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div
      style={{
        padding: "1.5rem",
        borderRadius: 16,
        background: "#020617",
        border: "1px solid #1f2937",
      }}
    >
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.5rem" }}>
        Работники и доступ к дашборду
      </h2>
      <p style={{ color: "#9ca3af", fontSize: "0.9rem", marginBottom: "1rem" }}>
        Включите или отключите право на просмотр дашборда для каждого работника.
      </p>
      {loading && <p style={{ color: "#9ca3af" }}>Загружаем...</p>}
      {error && <p style={{ color: "#fecaca" }}>{error}</p>}
      {!loading && !error && workers.length === 0 && (
        <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
          Нет зарегистрированных работников.
        </p>
      )}
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {workers.map((w) => (
          <div
            key={w.id}
            style={{
              padding: "0.75rem 1rem",
              borderRadius: 12,
              border: "1px solid #111827",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontWeight: 500 }}>{w.username}</span>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <span style={{ fontSize: "0.85rem", color: "#9ca3af" }}>
                Доступ к дашборду
              </span>
              <input
                type="checkbox"
                checked={w.can_view_dashboard}
                disabled={updatingId === w.id}
                onChange={() => handleToggle(w)}
                style={{ width: 18, height: 18, cursor: updatingId === w.id ? "default" : "pointer" }}
              />
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
