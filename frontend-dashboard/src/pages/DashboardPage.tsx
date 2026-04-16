import { useEffect, useState } from "react";
import { fetchDashboardState, DashboardState } from "../api/dashboardApi";
import {
  Device,
  fetchAssignedDevices,
  fetchDeviceByUid,
  fetchDeviceHeartbeats,
  DeviceHeartbeat,
} from "../api/devicesApi";
import { createDeviceLink, deleteDeviceLink, updateDeviceLink } from "../api/automationApi";
import { controlActuator } from "../api/actuatorsApi";
import { DeviceInfoBlock } from "../components/DeviceInfoBlock";
import { DeviceManagementBlock } from "../components/DeviceManagementBlock";
import { DeviceHistoryBlock } from "../components/DeviceHistoryBlock";

interface DashboardPageProps {
  isAdmin: boolean;
}

export function DashboardPage({ isAdmin }: DashboardPageProps) {
  const HEARTBEAT_ONLINE_SENSOR_SECONDS = 20;
  const HEARTBEAT_ONLINE_ACTUATOR_SECONDS = 20;
  const HEARTBEAT_ONLINE_DEFAULT_SECONDS = 25;
  const [state, setState] = useState<DashboardState | null>(null);
  const [assignedDevices, setAssignedDevices] = useState<Device[]>([]);
  const [heartbeats, setHeartbeats] = useState<Record<string, DeviceHeartbeat>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailsUid, setDetailsUid] = useState<string | null>(null);
  const [detailsDevice, setDetailsDevice] = useState<Device | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [linkSourceUid, setLinkSourceUid] = useState("");
  const [linkTargetUid, setLinkTargetUid] = useState("");
  const [linkController, setLinkController] = useState("");
  const [linkDescription, setLinkDescription] = useState("");
  const [linkMinValue, setLinkMinValue] = useState("");
  const [linkMaxValue, setLinkMaxValue] = useState("");
  const [linkAutoControlEnabled, setLinkAutoControlEnabled] = useState(false);
  const [linkSaving, setLinkSaving] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  const parseThresholdValue = (raw: string): number | undefined => {
    const normalized = raw.trim().replace(",", ".");
    if (!normalized) return undefined;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, assignedData, heartbeatsData] = await Promise.all([
        fetchDashboardState(),
        fetchAssignedDevices(),
        fetchDeviceHeartbeats(),
      ]);
      setState(dashboardData);
      setAssignedDevices(assignedData);
      setHeartbeats(heartbeatsData || {});
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
    }, 2000);
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

  const getOnlineTimeoutSeconds = (deviceType: string): number => {
    const normalized = (deviceType || "").toUpperCase();
    if (normalized.includes("SENSOR")) return HEARTBEAT_ONLINE_SENSOR_SECONDS;
    if (normalized.includes("ACTUATOR")) return HEARTBEAT_ONLINE_ACTUATOR_SECONDS;
    return HEARTBEAT_ONLINE_DEFAULT_SECONDS;
  };

  const formatHeartbeatTs = (tsRaw?: string): string => {
    if (!tsRaw) return "нет данных";
    const ts = Date.parse(tsRaw);
    if (Number.isNaN(ts)) return "нет данных";
    return new Date(ts).toLocaleTimeString();
  };

  const getOnlineStatus = (
    deviceUid: string,
    fallbackDeviceType?: string,
  ): { online: boolean; label: "Онлайн" | "Офлайн"; title: string } => {
    const heartbeat = heartbeats?.[deviceUid];
    const tsRaw = heartbeat?.ts;
    const heartbeatDeviceType = heartbeat?.device_type || fallbackDeviceType || "";
    const timeoutSeconds = getOnlineTimeoutSeconds(heartbeatDeviceType);
    const lastPulse = formatHeartbeatTs(tsRaw);
    if (!tsRaw) {
      return {
        online: false,
        label: "Офлайн",
        title: `Последний пульс: ${lastPulse}`,
      };
    }
    const ts = Date.parse(tsRaw);
    if (Number.isNaN(ts)) {
      return {
        online: false,
        label: "Офлайн",
        title: `Последний пульс: ${lastPulse}`,
      };
    }
    const online = Date.now() - ts <= timeoutSeconds * 1000;
    return {
      online,
      label: online ? "Онлайн" : "Офлайн",
      title: `Последний пульс: ${lastPulse}`,
    };
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
  const linkedActuatorUids = new Set(
    (state?.links || []).filter((l) => l.active).map((l) => l.target_device_uid),
  );
  const autoControlledActuatorUids = new Set(
    (state?.links || [])
      .filter((link) => link.active && Boolean(link.auto_control_enabled))
      .map((link) => link.target_device_uid),
  );

  const saveLink = async () => {
    if (!linkSourceUid || !linkTargetUid) return;
    setLinkSaving(true);
    setLinkError(null);
    try {
      await createDeviceLink({
        source_device_uid: linkSourceUid,
        target_device_uid: linkTargetUid,
        controller: linkController || undefined,
        description: linkDescription || undefined,
        active: true,
        auto_control_enabled: linkAutoControlEnabled,
        min_value: parseThresholdValue(linkMinValue),
        max_value: parseThresholdValue(linkMaxValue),
      });
      setLinkDescription("");
      setLinkMinValue("");
      setLinkMaxValue("");
      setLinkAutoControlEnabled(false);
      await load();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setLinkError(typeof detail === "string" ? detail : "Не удалось создать связь");
    } finally {
      setLinkSaving(false);
    }
  };

  const removeLink = async (linkId: number) => {
    await deleteDeviceLink(linkId);
    await load();
  };

  const toggleAutoMode = async (linkId: number, current: boolean) => {
    await updateDeviceLink(linkId, { auto_control_enabled: !current });
    await load();
  };

  const setLinkThresholds = async (linkId: number, minValue?: number | null, maxValue?: number | null) => {
    await updateDeviceLink(linkId, { min_value: minValue ?? null, max_value: maxValue ?? null });
    await load();
  };

  const handleManualActuator = async (deviceUid: string, actuatorType: string, action: "ON" | "OFF") => {
    await controlActuator({ device_uid: deviceUid, actuator_type: actuatorType, action });
    await load();
  };

  useEffect(() => {
    let mounted = true;
    load();
    const id = setInterval(() => {
      if (mounted) load();
    }, 2000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <>
      <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "1fr 1fr" }}>
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
          {loading}
          {error && <p style={{ color: "#fecaca" }}>{error}</p>}
          {!loading && !error && state && state.sensors.length === 0 && (
            <p style={{ color: "#6b7280", fontSize: "0.9rem" }}>
              Данных с датчиков пока нет. После установки датчика админом эмулятор запускается автоматически.
            </p>
          )}
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {state?.sensors.map((s) => (
              <div key={`${s.device_uid}-${s.created_at}`} style={cardStyle}>
                {(() => {
                  const device = assignedDevices.find((d) => d.device_uid === s.device_uid);
                  const isActive = device?.status === "active";
                  const acceptsData = device?.accepts_data !== false;
                  const acceptsDataLabel = acceptsData ? "Принимаем данные" : "Не принимаем данные";
                  const onlineStatus = getOnlineStatus(s.device_uid, device?.device_type || s.sensor_type || "");
                  return (
                    <div>
                      <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{"UID датчика: "}{s.device_uid}</div>
                      {isActive ? (
                        <>
                          <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                            {"Тип датчика:"} {device?.device_type || s.sensor_type || "sensor"}
                          </div>
                          <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                            {"Значение:"} {s.value}
                          </div>
                          <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                            <span
                              style={{
                                width: 10,
                                height: 10,
                                borderRadius: "50%",
                                display: "inline-block",
                                background: onlineStatus.online ? "#22c55e" : "#ef4444",
                              }}
                            />
                            <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                              {onlineStatus.label}
                            </span>
                          </div>
                          {!acceptsData && (
                            <div style={{ marginTop: 4, fontSize: "0.75rem", color: "#9ca3af" }}>
                              Состояние: {acceptsDataLabel}
                            </div>
                          )}
                          <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                            <span
                              style={{
                                width: 10,
                                height: 10,
                                borderRadius: "50%",
                                display: "inline-block",
                                background:
                                  s.indicator === "green"
                                    ? "#22c55e"
                                    : s.indicator === "yellow"
                                      ? "#facc15"
                                      : s.indicator === "red"
                                        ? "#ef4444"
                                        : "#ffffff",
                              }}
                            />
                            <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
                              Состояние:{" "}
                              {s.indicator === "red"
                                ? "Критическое"
                                : s.indicator === "yellow"
                                ? "Граничное"
                                : s.indicator === "green"
                                ? "Хорошее"
                                : "Не связан"}
                              {s.min_value != null || s.max_value != null
                                ? ` (норма ${s.min_value ?? "-"}..${s.max_value ?? "-"})`
                                : ""}
                            </span>
                          </div>
                        </>
                      ) : (
                        <>
                          <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                            {"Тип датчика:"} {device?.device_type || s.sensor_type || "sensor"}
                          </div>
                          <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                            <span
                              style={{
                                width: 10,
                                height: 10,
                                borderRadius: "50%",
                                display: "inline-block",
                                background: onlineStatus.online ? "#22c55e" : "#ef4444",
                              }}
                            />
                            <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                              {onlineStatus.label}
                            </span>
                          </div>
                          {!acceptsData && (
                            <div style={{ marginTop: 4, fontSize: "0.75rem", color: "#9ca3af" }}>
                              Состояние: {acceptsDataLabel}
                            </div>
                          )}
                          <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>Датчик не активен</div>
                        </>
                      )}
                    </div>
                  );
                })()}
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
                {(() => {
                  const onlineStatus = getOnlineStatus(d.device_uid, d.device_type || "");
                  const acceptsData = d.accepts_data !== false;
                  const acceptsDataLabel = acceptsData ? "Принимаем данные" : "Не принимаем данные";
                  return (
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{"UID датчика: "}{d.device_uid}</div>
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {"Тип датчика:"} {d.device_type || "SENSOR"}
                  </div>
                  <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        display: "inline-block",
                        background: onlineStatus.online ? "#22c55e" : "#ef4444",
                      }}
                    />
                    <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                      {onlineStatus.label}
                    </span>
                  </div>
                  {!acceptsData && (
                    <div style={{ marginTop: 4, fontSize: "0.75rem", color: "#9ca3af" }}>
                      Состояние: {acceptsDataLabel}
                    </div>
                  )}
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {"Статус: "}{d.status === "active" ? "ожидание первых данных" : "Датчик не активен"}
                  </div>
                </div>
                  );
                })()}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
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
                  {(() => {
                    const device = assignedDevices.find((d) => d.device_uid === a.device_uid);
                    const isActive = device?.status === "active";
                    const onlineStatus = getOnlineStatus(a.device_uid, device?.device_type || a.actuator_type || "");
                    const isAutoControlled = autoControlledActuatorUids.has(a.device_uid);
                    const isLinked = linkedActuatorUids.has(a.device_uid);
                    const normalizedState = (a.state ?? "").trim().toUpperCase();
                    const showLinkedState = isLinked && (normalizedState === "ON" || normalizedState === "OFF");
                    const isManualControlDisabled = isAutoControlled || !isLinked;
                    const statusLabel = !isLinked
                      ? "не связан"
                      : showLinkedState
                        ? normalizedState
                        : "состояние ещё не получено";
                    const statusDotColor = !isLinked
                      ? "#ffffff"
                      : normalizedState === "ON"
                        ? "#22c55e"
                        : normalizedState === "OFF"
                          ? "#ef4444"
                          : "#ffffff";
                    const statusTextColor = !isLinked
                      ? "#ffffff"
                      : normalizedState === "ON"
                        ? "#bbf7d0"
                        : normalizedState === "OFF"
                          ? "#fecaca"
                          : "#ffffff";
                    return (
                      <>
                        <div>
                          <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{"UID актуатора: "}{a.device_uid}</div>
                          {isActive ? (
                            <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                              {"Тип устройства: "}{a.actuator_type}
                              <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                                <span
                                  style={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: "50%",
                                    display: "inline-block",
                                    background: onlineStatus.online ? "#22c55e" : "#ef4444",
                                  }}
                                />
                                <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                                  {onlineStatus.label}
                                </span>
                              </div>
                              <div>
                                <span style = {{fontSize: "0.95rem", fontWeight: 500}}> {"Состояние: "}</span>
                                <span
                                  style={{
                                    color: statusTextColor,
                                    fontWeight: 600,
                                  }}
                                >
                                  {statusLabel}
                                </span><span>{"  "}</span>
                                <span
                                  style={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: "50%",
                                    display: "inline-block",
                                    marginRight: 6,
                                    background: statusDotColor,
                                  }}
                                />
                              </div>
                            </div>
                          ) : (
                            <>
                              <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                                {"Тип устройства: "}{device?.device_type || a.actuator_type}
                              </div>
                              <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                                <span
                                  style={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: "50%",
                                    display: "inline-block",
                                    background: onlineStatus.online ? "#22c55e" : "#ef4444",
                                  }}
                                />
                                <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                                  {onlineStatus.label}
                                </span>
                              </div>
                              <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>Актуатор не активен</div>
                            </>
                          )}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {isAdmin && (
                            <>
                              <button
                                type="button"
                                disabled={isManualControlDisabled}
                                onClick={() => handleManualActuator(a.device_uid, a.actuator_type, "ON")}
                                style={{
                                  padding: "0.2rem 0.45rem",
                                  fontSize: "0.72rem",
                                  borderRadius: 6,
                                  border: "1px solid #14532d",
                                  background: "transparent",
                                  color: isManualControlDisabled ? "#6b7280" : "#bbf7d0",
                                  cursor: isManualControlDisabled ? "not-allowed" : "pointer",
                                  opacity: isManualControlDisabled ? 0.55 : 1,
                                }}
                              >
                                ON
                              </button>
                              <button
                                type="button"
                                disabled={isManualControlDisabled}
                                onClick={() => handleManualActuator(a.device_uid, a.actuator_type, "OFF")}
                                style={{
                                  padding: "0.2rem 0.45rem",
                                  fontSize: "0.72rem",
                                  borderRadius: 6,
                                  border: "1px solid #7f1d1d",
                                  background: "transparent",
                                  color: isManualControlDisabled ? "#6b7280" : "#fecaca",
                                  cursor: isManualControlDisabled ? "not-allowed" : "pointer",
                                  opacity: isManualControlDisabled ? 0.55 : 1,
                                }}
                              >
                                OFF
                              </button>
                            </>
                          )}
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
                      </>
                    );
                  })()}
                </div>
              ))}
              {actuatorDevicesWithoutData.map((d) => (
                <div key={d.device_uid} style={cardStyle}>
                  {(() => {
                    const onlineStatus = getOnlineStatus(d.device_uid, d.device_type || "");
                    return (
                  <div>
                    <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{"UID актуатора:"} {d.device_uid}</div>
                    <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                      {"Тип устройства: "}{d.device_type}
                      <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                        <span
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            display: "inline-block",
                            background: onlineStatus.online ? "#22c55e" : "#ef4444",
                          }}
                        />
                        <span style={{ fontSize: "0.75rem", color: "#9ca3af" }} title={onlineStatus.title}>
                          {onlineStatus.label}
                        </span>
                      </div>
                      {d.status === "active" ? (
                        <div style={{ marginTop: 4 }}>
                          <span style={{ fontSize: "0.95rem", fontWeight: 500 }}>{"Состояние: "}</span>
                          <span style={{ fontWeight: 600 }}>
                            {linkedActuatorUids.has(d.device_uid) ? "состояние ещё не получено" : "не связан"}
                          </span>
                          <span>{"  "}</span>
                          <span
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: "50%",
                              display: "inline-block",
                              marginRight: 6,
                              background: "#ffffff",
                            }}
                          />
                        </div>
                      ) : (
                        <div style={{ marginTop: 4, fontSize: "0.95rem", fontWeight: 500 }}>
                          Актуатор не активен
                        </div>
                      )}
                    </div>
                  </div>
                    );
                  })()}
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
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
          <>
            <div
              style={{
                display: "grid",
                gap: "0.5rem",
                gridTemplateColumns: "1fr 1fr 1fr 1fr 0.8fr auto",
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
              value={linkDescription}
              onChange={(e) => setLinkDescription(e.target.value)}
              placeholder="Комментарий связи"
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            />
            <input
              value={linkMinValue}
              onChange={(e) => setLinkMinValue(e.target.value)}
              placeholder="Мин. норма"
              type="number"
              style={{ padding: "0.5rem", borderRadius: 8, background: "#0f172a", color: "#e5e7eb", border: "1px solid #1f2937" }}
            />
            <input
              value={linkMaxValue}
              onChange={(e) => setLinkMaxValue(e.target.value)}
              placeholder="Макс. норма"
              type="number"
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
            <label style={{ display: "flex", alignItems: "center", gap: 6, color: "#9ca3af", fontSize: "0.8rem" }}>
              <input
                type="checkbox"
                checked={linkAutoControlEnabled}
                onChange={(e) => setLinkAutoControlEnabled(e.target.checked)}
              />
              Авто
            </label>
            </div>
            {linkError && (
              <p style={{ marginTop: "0.5rem", color: "#fecaca", fontSize: "0.85rem" }}>
                {linkError}
              </p>
            )}
          </>
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
                  {"[Датчик:"} {link.source_device_uid}{"] связан с [Актуатор:"}  {link.target_device_uid}{"]"}
                </div>
                <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                  {[link.description ? `Описание: ${link.description}` : null]
                    .filter(Boolean)
                    .join(" · ") || "Без дополнительных данных"}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: 4 }}>
                  Авто: {link.auto_control_enabled ? "вкл" : "выкл"} · Пороги: {link.min_value ?? "-"}..{link.max_value ?? "-"}
                </div>
              </div>
              {isAdmin && (
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    type="button"
                    onClick={() => toggleAutoMode(link.id, Boolean(link.auto_control_enabled))}
                    style={{
                      padding: "0.25rem 0.5rem",
                      fontSize: "0.75rem",
                      borderRadius: 6,
                      border: link.auto_control_enabled ? "1px solid #14532d" : "1px solid #374151",
                      background: link.auto_control_enabled ? "rgba(34,197,94,0.15)" : "transparent",
                      color: link.auto_control_enabled ? "#bbf7d0" : "#9ca3af",
                      cursor: "pointer",
                    }}
                  >
                    Auto {link.auto_control_enabled ? "ON" : "OFF"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const minRaw = window.prompt("Минимальная норма", link.min_value?.toString() ?? "");
                      const maxRaw = window.prompt("Максимальная норма", link.max_value?.toString() ?? "");
                      if (minRaw === null || maxRaw === null) return;
                      setLinkThresholds(
                        link.id,
                        minRaw.trim() === "" ? null : Number(minRaw),
                        maxRaw.trim() === "" ? null : Number(maxRaw),
                      );
                    }}
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
                    Пороги
                  </button>
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
                </div>
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

