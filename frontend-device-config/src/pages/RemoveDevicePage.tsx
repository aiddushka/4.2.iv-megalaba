import { useEffect, useMemo, useState } from "react";
import {
  deleteDevicePublic,
  fetchDevicesPublic,
  PublicDeviceRow,
  setDeviceRuntimePublic,
} from "../api/devicesApi";

type RuntimeStatus = "active" | "disabled";

const btnBase: React.CSSProperties = {
  padding: "0.35rem 0.65rem",
  fontSize: "0.8rem",
  borderRadius: 8,
  background: "transparent",
  cursor: "pointer",
  border: "1px solid #374151",
};

export function RemoveDevicePage() {
  const [devices, setDevices] = useState<PublicDeviceRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyUid, setBusyUid] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDevicesPublic();
      setDevices(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Не удалось загрузить список устройств");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = window.setInterval(load, 2500);
    return () => window.clearInterval(id);
  }, []);

  const rows = useMemo(() => {
    return [...devices].sort((a, b) => a.device_uid.localeCompare(b.device_uid));
  }, [devices]);

  const setRuntime = async (uid: string, status: RuntimeStatus) => {
    setBusyUid(uid);
    setError(null);
    try {
      await setDeviceRuntimePublic(uid, status);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Не удалось изменить состояние устройства");
    } finally {
      setBusyUid(null);
    }
  };

  const remove = async (uid: string) => {
    if (!window.confirm(`Удалить устройство "${uid}"? Это удалит данные в бекенде и остановит контейнер.`)) return;
    setBusyUid(uid);
    setError(null);
    try {
      await deleteDevicePublic(uid);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Не удалось удалить устройство");
    } finally {
      setBusyUid(null);
    }
  };

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        padding: "1.5rem",
        background: "#020617",
        borderRadius: 16,
        boxShadow: "0 25px 50px -12px rgba(15,23,42,0.8)",
        border: "1px solid #111827",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "1rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: 0 }}>Удаление устройств</h2>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          style={{
            ...btnBase,
            border: "1px solid #1f2937",
            color: "#9ca3af",
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          Обновить
        </button>
      </div>

      <p style={{ color: "#9ca3af", fontSize: "0.9rem", marginTop: 10 }}>
        Здесь можно выключать/включать устройства (старт/стоп контейнера) и удалять их полностью.
      </p>

      {error && (
        <div
          style={{
            marginTop: "0.75rem",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            background: "rgba(239,68,68,0.1)",
            color: "#fecaca",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}

      <div style={{ marginTop: "1rem", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0 }}>
          <thead>
            <tr>
              {["uid", "тип устройства", "место установки", "с кем связь", "вкл/выкл", "удалить"].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    fontSize: "0.8rem",
                    color: "#9ca3af",
                    fontWeight: 600,
                    padding: "0.75rem 0.75rem",
                    borderBottom: "1px solid #1f2937",
                    background: "#020617",
                    position: "sticky",
                    top: 0,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => {
              const status = (d.status || "").toLowerCase();
              const isActive = status === "active";
              const isDisabled = status === "disabled";
              const busy = busyUid === d.device_uid;
              return (
                <tr key={d.device_uid}>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827" }}>{d.device_uid}</td>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827", color: "#e5e7eb" }}>
                    {d.device_type}
                  </td>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827", color: "#9ca3af" }}>
                    {d.location || "—"}
                  </td>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827", color: "#9ca3af" }}>
                    {d.linked_device_uids?.length ? d.linked_device_uids.join(", ") : "—"}
                  </td>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827" }}>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        disabled={busy || isActive}
                        onClick={() => setRuntime(d.device_uid, "active")}
                        style={{
                          ...btnBase,
                          border: "1px solid #14532d",
                          color: isActive ? "#6b7280" : "#bbf7d0",
                          cursor: busy || isActive ? "not-allowed" : "pointer",
                          opacity: busy || isActive ? 0.55 : 1,
                        }}
                        title={isActive ? "Устройство уже включено" : "Включить устройство"}
                      >
                        Включить
                      </button>
                      <button
                        type="button"
                        disabled={busy || isDisabled}
                        onClick={() => setRuntime(d.device_uid, "disabled")}
                        style={{
                          ...btnBase,
                          border: "1px solid #7f1d1d",
                          color: isDisabled ? "#6b7280" : "#fecaca",
                          cursor: busy || isDisabled ? "not-allowed" : "pointer",
                          opacity: busy || isDisabled ? 0.55 : 1,
                        }}
                        title={isDisabled ? "Устройство уже выключено" : "Выключить устройство"}
                      >
                        Выключить
                      </button>
                    </div>
                  </td>
                  <td style={{ padding: "0.7rem 0.75rem", borderBottom: "1px solid #111827" }}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => remove(d.device_uid)}
                      style={{
                        ...btnBase,
                        border: "1px solid #7f1d1d",
                        color: "#fca5a5",
                        cursor: busy ? "not-allowed" : "pointer",
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              );
            })}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: "1rem 0.75rem", color: "#6b7280" }}>
                  Устройств пока нет.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

