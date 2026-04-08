import { useEffect, useState } from "react";
import { fetchDashboardState, DashboardState } from "../api/dashboardApi";
import { Device, fetchAssignedDevices, fetchDeviceByUid } from "../api/devicesApi";
import { createDeviceLink, deleteDeviceLink } from "../api/automationApi";
import { DeviceInfoBlock } from "../components/DeviceInfoBlock";
import { DeviceManagementBlock } from "../components/DeviceManagementBlock";
import { DeviceHistoryBlock } from "../components/DeviceHistoryBlock";

interface DashboardPageProps {
  isAdmin: boolean;
}

export function DashboardPage({ isAdmin }: DashboardPageProps) {
  const [state, setState] = useState<DashboardState | null>(null);
  const [assignedDevices, setAssignedDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailsUid, setDetailsUid] = useState<string | null>(null);
  const [detailsDevice, setDetailsDevice] = useState<Device | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [linkSourceUid, setLinkSourceUid] = useState("");
  const [linkTargetUid, setLinkTargetUid] = useState("");
  const [linkController, setLinkController] = useState("");
  const [linkDescription, setLinkDescription] = useState("");
  const [linkSaving, setLinkSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, assignedData] = await Promise.all([
        fetchDashboardState(),
        fetchAssignedDevices(),
      ]);
      setState(dashboardData);
      setAssignedDevices(assignedData);
    } catch (e: unknown) {
      setError("Не удалось загрузить состояние теплицы");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    load();
    const id = setInterval(() => {
      if (mounted) load();
    }, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const openDetails = async (deviceUid: string) => {
    setDetailsUid(deviceUid);
    setDetailsLoading(true);
    try {
      const data = await fetchDeviceByUid(deviceUid);
      setDetailsDevice(data);
    } finally {
      setDetailsLoading(false);
    }
  };
  const closeDetails = () => {
    setDetailsUid(null);
    setDetailsDevice(null);
  };

  const cardStyle: React.CSSProperties = {
    padding: "0.75rem 1rem",
    borderRadius: 12,
    background: "#020617",
    border: "1px solid #111827",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  };

  const sensorsWithData = new Set((state?.sensors || []).map((s) => s.device_uid));
  const actuatorsWithData = new Set((state?.actuators || []).map((a) => a.device_uid));
  const sensorDevices = assignedDevices.filter((d) => d.device_type.includes("SENSOR"));
  const actuatorDevices = assignedDevices.filter((d) => d.device_type.includes("ACTUATOR"));
  const sensorDevicesWithoutData = assignedDevices.filter(
    (d) => d.device_type.includes("SENSOR") && !sensorsWithData.has(d.device_uid),
  );
  const actuatorDevicesWithoutData = assignedDevices.filter(
    (d) => d.device_type.includes("ACTUATOR") && !actuatorsWithData.has(d.device_uid),
  );

  const saveLink = async () => {
    if (!linkSourceUid || !linkTargetUid) return;
    setLinkSaving(true);
    try {
      await createDeviceLink({
        source_device_uid: linkSourceUid,
        target_device_uid: linkTargetUid,
        controller: linkController || undefined,
        description: linkDescription || undefined,
        active: true,
      });
      setLinkDescription("");
      await load();
    } finally {
      setLinkSaving(false);
    }
  };

  const removeLink = async (linkId: number) => {
    await deleteDeviceLink(linkId);
    await load();
  };

  return (
    <>
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
              <div key={`${s.device_uid}-${s.created_at}`} style={cardStyle}>
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{s.device_uid}</div>
                  {(s.description || s.location) && (
                    <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                      {[s.description, s.location].filter(Boolean).join(" · ")}
                    </div>
                  )}
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {s.sensor_type || "sensor"}: {s.value}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                    {new Date(s.created_at).toLocaleTimeString()}
                  </span>
                  <button
                    type="button"
                    onClick={() => openDetails(s.device_uid)}
                    style={{
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.75rem",
                      borderRadius: 6,
                      border: "1px solid #374151",
                      background: "transparent",
                      color: "#9ca3af",
                      cursor: "pointer",
                    }}
                  >
                    Подробнее
                  </button>
                </div>
              </div>
            ))}
            {sensorDevicesWithoutData.map((d) => (
              <div key={d.device_uid} style={cardStyle}>
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{d.device_uid}</div>
                  {(d.description || d.location) && (
                    <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                      {[d.description, d.location].filter(Boolean).join(" · ")}
                    </div>
                  )}
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {d.device_type}: ожидание первых данных
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => openDetails(d.device_uid)}
                  style={{
                    padding: "0.25rem 0.5rem",
                    fontSize: "0.75rem",
                    borderRadius: 6,
                    border: "1px solid #374151",
                    background: "transparent",
                    color: "#9ca3af",
                    cursor: "pointer",
                  }}
                >
                  Подробнее
                </button>
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
          {!state || (state.actuators.length === 0 && actuatorDevicesWithoutData.length === 0) ? (
            <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
              Состояний актуаторов пока нет. Запусти эмуляторы в папке `device-emulator/actuators`
              или отправь команды через API.
            </p>
          ) : (
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {state.actuators.map((a) => (
                <div key={a.device_uid} style={cardStyle}>
                  <div>
                    <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{a.device_uid}</div>
                    {(a.description || a.location) && (
                      <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                        {[a.description, a.location].filter(Boolean).join(" · ")}
                      </div>
                    )}
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
                  <button
                    type="button"
                    onClick={() => openDetails(a.device_uid)}
                    style={{
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.75rem",
                      borderRadius: 6,
                      border: "1px solid #374151",
                      background: "transparent",
                      color: "#9ca3af",
                      cursor: "pointer",
                    }}
                  >
                    Подробнее
                  </button>
                </div>
              ))}
              {actuatorDevicesWithoutData.map((d) => (
                <div key={d.device_uid} style={cardStyle}>
                  <div>
                    <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{d.device_uid}</div>
                    {(d.description || d.location) && (
                      <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                        {[d.description, d.location].filter(Boolean).join(" · ")}
                      </div>
                    )}
                    <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                      {d.device_type}: состояние ещё не получено
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => openDetails(d.device_uid)}
                    style={{
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.75rem",
                      borderRadius: 6,
                      border: "1px solid #374151",
                      background: "transparent",
                      color: "#9ca3af",
                      cursor: "pointer",
                    }}
                  >
                    Подробнее
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
      <section
        style={{
          marginTop: "1.5rem",
          padding: "1.5rem",
          borderRadius: 16,
          background: "#020617",
          border: "1px solid #1f2937",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>
          Связи датчиков и актуаторов
        </h2>
        <p style={{ color: "#9ca3af", fontSize: "0.9rem", marginBottom: "1rem" }}>
          Здесь видно, какие устройства связаны между собой (датчик to актуатор/исполнитель).
        </p>
        {isAdmin && (
          <div
            style={{
              display: "grid",
              gap: "0.5rem",
              gridTemplateColumns: "1fr 1fr 1fr 1fr auto",
              marginBottom: "1rem",
            }}
          >
            <select
              value={linkSourceUid}
              onChange={(e) => setLinkSourceUid(e.target.value)}
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            >
              <option value="">Выбери датчик</option>
              {sensorDevices.map((d) => (
                <option key={d.device_uid} value={d.device_uid}>
                  {d.device_uid}
                </option>
              ))}
            </select>
            <select
              value={linkTargetUid}
              onChange={(e) => setLinkTargetUid(e.target.value)}
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            >
              <option value="">Выбери актуатор</option>
              {actuatorDevices.map((d) => (
                <option key={d.device_uid} value={d.device_uid}>
                  {d.device_uid}
                </option>
              ))}
            </select>
            <input
              value={linkController}
              onChange={(e) => setLinkController(e.target.value)}
              placeholder="Контроллер (опц.)"
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            />
            <input
              value={linkDescription}
              onChange={(e) => setLinkDescription(e.target.value)}
              placeholder="Комментарий связи"
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            />
            <button
              type="button"
              onClick={saveLink}
              disabled={linkSaving || !linkSourceUid || !linkTargetUid}
              style={{
                padding: "0.5rem 0.75rem",
                borderRadius: 8,
                border: "none",
                background: linkSaving ? "#4b5563" : "linear-gradient(90deg,#22c55e,#22d3ee)",
                color: "#020617",
                fontWeight: 600,
                cursor: linkSaving ? "default" : "pointer",
              }}
            >
              {linkSaving ? "Сохраняем..." : "Связать"}
            </button>
          </div>
        )}
        <div style={{ display: "grid", gap: "0.75rem" }}>
          {(state?.links || []).length === 0 && (
            <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
              Связей пока нет.
            </p>
          )}
          {state?.links.map((link) => (
            <div key={link.id} style={cardStyle}>
              <div>
                <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                  {link.source_device_uid} {"->"}{" "}
                  {link.target_device_uid}
                </div>
                <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                  {[link.controller ? `Контроллер: ${link.controller}` : null, link.description]
                    .filter(Boolean)
                    .join(" · ") || "Без дополнительных данных"}
                </div>
              </div>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => removeLink(link.id)}
                  style={{
                    padding: "0.25rem 0.5rem",
                    fontSize: "0.75rem",
                    borderRadius: 6,
                    border: "1px solid #7f1d1d",
                    background: "transparent",
                    color: "#fca5a5",
                    cursor: "pointer",
                  }}
                >
                  Удалить
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      {detailsUid && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
          onClick={closeDetails}
        >
          <div
            style={{
              background: "#0f172a",
              padding: "1.5rem",
              borderRadius: 16,
              border: "1px solid #1f2937",
              minWidth: 320,
              width: "min(920px, 95vw)",
              maxHeight: "90vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>
              Подробнее: {detailsUid}
            </h3>
            {detailsLoading && <p style={{ color: "#9ca3af" }}>Загружаем устройство...</p>}
            {!detailsLoading && detailsDevice && (
              <div style={{ display: "grid", gap: "0.75rem" }}>
                <DeviceInfoBlock device={detailsDevice} />
                {isAdmin && (
                  <>
                    <DeviceManagementBlock
                      device={detailsDevice}
                      isAdmin={isAdmin}
                      onSaved={async () => {
                        const refreshed = await fetchDeviceByUid(detailsDevice.device_uid);
                        setDetailsDevice(refreshed);
                        await load();
                      }}
                    />
                    <DeviceHistoryBlock device={detailsDevice} />
                  </>
                )}
              </div>
            )}
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={closeDetails}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: 8,
                  border: "1px solid #374151",
                  background: "transparent",
                  color: "#9ca3af",
                  cursor: "pointer",
                }}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

