import { useEffect, useState } from "react";
import { Device, updateDeviceConfig } from "../api/devicesApi";

interface Props {
  device: Device;
  isAdmin: boolean;
  onSaved: () => Promise<void> | void;
}

export function DeviceManagementBlock({ device, isAdmin, onSaved }: Props) {
  const [status, setStatus] = useState(device.status || "active");
  const [location, setLocation] = useState(device.location || "");
  const [lastMaintenance, setLastMaintenance] = useState(
    device.last_maintenance ? device.last_maintenance.slice(0, 10) : "",
  );
  const [maintenanceNotes, setMaintenanceNotes] = useState(device.maintenance_notes || "");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setStatus(device.status || "active");
    setLocation(device.location || "");
    setLastMaintenance(device.last_maintenance ? device.last_maintenance.slice(0, 10) : "");
    setMaintenanceNotes(device.maintenance_notes || "");
  }, [device]);

  const save = async () => {
    setSaving(true);
    setNotice(null);
    try {
      await updateDeviceConfig(device.device_uid, {
        location,
        status: isAdmin ? status : undefined,
        last_maintenance: isAdmin && lastMaintenance ? new Date(lastMaintenance).toISOString() : undefined,
        maintenance_notes: isAdmin ? maintenanceNotes : undefined,
      });
      await onSaved();
      setNotice("Изменения успешно сохранены");
    } catch {
      setNotice("Не удалось сохранить изменения");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ border: "1px solid #1f2937", borderRadius: 12, background: "#020617", padding: "1rem" }}>
      <h4 style={{ margin: "0 0 0.75rem 0", color: "#22c55e" }}>Управление устройством</h4>
      <div style={{ marginBottom: 8 }}>
        <label style={{ display: "block", fontSize: "0.8rem", color: "#9ca3af", marginBottom: 4 }}>
          Состояние
        </label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          disabled={!isAdmin}
          style={{ width: "100%", padding: "0.5rem", background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, color: "#e5e7eb" }}
        >
          <option value="active">Активно</option>
          <option value="maintenance">Обслуживание</option>
          <option value="offline">Не в сети</option>
        </select>
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={{ display: "block", fontSize: "0.8rem", color: "#9ca3af", marginBottom: 4 }}>
          Место установки
        </label>
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          style={{ width: "100%", padding: "0.5rem", background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, color: "#e5e7eb", boxSizing: "border-box" }}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={{ display: "block", fontSize: "0.8rem", color: "#9ca3af", marginBottom: 4 }}>
          Дата последнего обслуживания
        </label>
        <input
          type="date"
          value={lastMaintenance}
          onChange={(e) => setLastMaintenance(e.target.value)}
          disabled={!isAdmin}
          style={{ width: "100%", padding: "0.5rem", background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, color: "#e5e7eb", boxSizing: "border-box" }}
        />
      </div>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontSize: "0.8rem", color: "#9ca3af", marginBottom: 4 }}>
          Заметки по обслуживанию
        </label>
        <textarea
          value={maintenanceNotes}
          onChange={(e) => setMaintenanceNotes(e.target.value)}
          disabled={!isAdmin}
          rows={4}
          style={{ width: "100%", padding: "0.5rem", background: "#0f172a", border: "1px solid #1f2937", borderRadius: 8, color: "#e5e7eb", boxSizing: "border-box" }}
        />
      </div>
      <button
        type="button"
        onClick={save}
        disabled={saving}
        style={{ padding: "0.5rem 1rem", borderRadius: 8, border: "none", background: saving ? "#4b5563" : "linear-gradient(90deg,#22c55e,#22d3ee)", color: "#020617", fontWeight: 600, cursor: saving ? "default" : "pointer" }}
      >
        {saving ? "Сохраняем..." : "Сохранить изменения"}
      </button>
      {notice && <div style={{ marginTop: 8, color: notice.includes("успешно") ? "#bbf7d0" : "#fecaca", fontSize: "0.8rem" }}>{notice}</div>}
    </div>
  );
}
