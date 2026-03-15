import { useEffect, useState } from "react";
import { assignDevice, fetchUnassignedDevices, Device } from "../api/devicesApi";

export function UnassignedDevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assigningId, setAssigningId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUnassignedDevices();
      setDevices(data);
    } catch (e) {
      setError("Не удалось загрузить список устройств");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAssign = async (device: Device) => {
    const location = window.prompt(
      "Укажите место установки для устройства:",
      device.location || "Теплица А, грядка 1",
    );
    if (!location) return;
    setAssigningId(device.id);
    try {
      await assignDevice({ device_uid: device.device_uid, location });
      await load();
    } finally {
      setAssigningId(null);
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
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
        Неустановленные устройства
      </h2>
      <p style={{ color: "#9ca3af", fontSize: "0.9rem", marginBottom: "1rem" }}>
        Это устройства, которые были зарегистрированы через конфигуратор (сайт №2), но ещё не
        размещены на доске. Выберите устройство и задайте место установки.
      </p>
      {loading && <p style={{ color: "#9ca3af" }}>Загружаем список...</p>}
      {error && <p style={{ color: "#fecaca" }}>{error}</p>}
      {!loading && !error && devices.length === 0 && (
        <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
          Нет неустановленных устройств. Зарегистрируй устройство через конфигуратор.
        </p>
      )}
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {devices.map((d) => (
          <div
            key={d.id}
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
              <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{d.device_uid}</div>
              <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>{d.device_type}</div>
              {d.description && (
                <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>{d.description}</div>
              )}
            </div>
            <button
              onClick={() => handleAssign(d)}
              disabled={assigningId === d.id}
              style={{
                padding: "0.4rem 0.9rem",
                borderRadius: 999,
                border: "none",
                background:
                  assigningId === d.id
                    ? "#4b5563"
                    : "linear-gradient(90deg,#22c55e,#22c55e)",
                color: "#020617",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: assigningId === d.id ? "default" : "pointer",
              }}
            >
              {assigningId === d.id ? "Устанавливаем..." : "Установить"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

