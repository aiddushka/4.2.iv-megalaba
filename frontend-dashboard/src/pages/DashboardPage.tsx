import { useEffect, useState } from "react";
import { fetchDashboardState, DashboardState } from "../api/dashboardApi";

export function DashboardPage() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchDashboardState();
        if (mounted) setState(data);
      } catch (e: any) {
        if (mounted) setError("Не удалось загрузить состояние теплицы");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "2fr 1fr" }}>
      <section
        style={{
          padding: "1.5rem",
          borderRadius: 16,
          background: "#020617",
          border: "1px solid #1f2937",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
          Датчики
        </h2>
        {loading && <p style={{ color: "#9ca3af" }}>Загружаем данные...</p>}
        {error && <p style={{ color: "#fecaca" }}>{error}</p>}
        {!loading && !error && state && state.sensors.length === 0 && (
          <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
            Данных с датчиков пока нет. Запусти эмуляторы в папке `device-emulator/sensors`.
          </p>
        )}
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {state?.sensors.map((s) => (
            <div
              key={`${s.device_uid}-${s.created_at}`}
              style={{
                padding: "0.75rem 1rem",
                borderRadius: 12,
                background: "#020617",
                border: "1px solid #111827",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{s.device_uid}</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                  {s.sensor_type || "sensor"}: {s.value}
                </div>
              </div>
              <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                {new Date(s.created_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section
        style={{
          padding: "1.5rem",
          borderRadius: 16,
          background: "#020617",
          border: "1px solid #1f2937",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
          Актуаторы
        </h2>
        {!state || state.actuators.length === 0 ? (
          <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
            Состояний актуаторов пока нет. Запусти эмуляторы в папке `device-emulator/actuators`
            или отправь команды через API.
          </p>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {state.actuators.map((a) => (
              <div
                key={a.device_uid}
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: 12,
                  background: "#020617",
                  border: "1px solid #111827",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{a.device_uid}</div>
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {a.actuator_type}:{" "}
                    <span
                      style={{
                        color: a.state === "ON" ? "#bbf7d0" : "#fca5a5",
                        fontWeight: 600,
                      }}
                    >
                      {a.state}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

