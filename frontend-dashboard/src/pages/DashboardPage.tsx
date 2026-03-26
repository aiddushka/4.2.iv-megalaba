import { useEffect, useState } from "react";
import { fetchDashboardState, DashboardState } from "../api/dashboardApi";
import { deleteDevice, updateDeviceConfig } from "../api/devicesApi";
import { controlActuator, setActuatorMode } from "../api/actuatorsApi";

interface DashboardPageProps {
  isAdmin: boolean;
}

export function DashboardPage({ isAdmin }: DashboardPageProps) {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingUid, setEditingUid] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editCatalogInfo, setEditCatalogInfo] = useState("");

  const [fullInfo, setFullInfo] = useState<{
    device_uid: string;
    title: string;
    text: string;
    location?: string | null;
  } | null>(null);

  const truncate = (text: string | null | undefined, maxLen: number) => {
    const t = (text ?? "").trim();
    if (!t) return "";
    if (t.length <= maxLen) return t;
    return t.slice(0, maxLen).trimEnd() + "...";
  };

  const getDeviceModelText = (args: {
    sensor_type?: string | null;
    actuator_type?: string | null;
  }) => {
    const sensorType = (args.sensor_type ?? "").toUpperCase();
    const actuatorType = (args.actuator_type ?? "").toUpperCase();

    if (sensorType === "TEMP_SENSOR") {
      return (
        "Модель работы (эмулятор): температура описывается суточным циклом " +
        "T(t)=T0 + A*sin(2πt/24h) + шум + медленный дрейф. " +
        "Так можно имитировать нагрев/охлаждение в теплице."
      );
    }
    if (sensorType === "HUMIDITY_AIR_SENSOR") {
      return (
        "Модель работы (эмулятор): влажность воздуха меняется в противофазе к температуре " +
        "(днём суше, ночью влажнее), добавлены гауссовский шум и небольшая вариативность."
      );
    }
    if (sensorType === "HUMIDITY_SOIL_SENSOR") {
      return (
        "Модель работы (эмулятор): влажность почвы убывает из‑за испарения, " +
        "редко происходят «поливы» (скачки влажности), плюс шум датчика. " +
        "Это похоже на поведение реального капельного/поливного контура."
      );
    }
    if (sensorType === "LIGHT_SENSOR") {
      return (
        "Модель работы (эмулятор): освещённость задаётся как функция времени суток " +
        "с дневным максимумом и редкими провалами (условные «облака»), " +
        "плюс шум измерений."
      );
    }

    if (actuatorType === "IRRIGATION_ACTUATOR") {
      return (
        "Модель работы (эмулятор): при команде ON устройство включает полив на фиксированное время " +
        "(эмулирует работу насоса/клапана), после чего автоматически переходит в OFF и публикует статус."
      );
    }
    if (actuatorType === "HEATER_ACTUATOR") {
      return (
        "Модель работы (эмулятор): при команде ON подогрев работает ограниченное время " +
        "(эмуляция тепловой инерции), затем OFF. Это подходит для демонстрации автоматики."
      );
    }
    if (actuatorType === "VENTILATION_ACTUATOR") {
      return (
        "Модель работы (эмулятор): вентиляция включается по команде ON на ограниченный интервал, " +
        "после чего выключается (эмуляция управления форточками/вентилятором)."
      );
    }
    if (actuatorType === "LIGHT_ACTUATOR") {
      return (
        "Модель работы (эмулятор): освещение переключается по командам ON/OFF и сразу публикует новый статус. " +
        "В простом демо нет сложного режима яркости."
      );
    }

    return "Модель работы (эмулятор): поведение устройства зависит от его типа (датчик/актуатор) и параметров теплицы.";
  };

  const handleDeleteDevice = async (deviceUid: string) => {
    const ok = window.confirm(`Удалить устройство ${deviceUid}? Скрипт эмулятора будет остановлен.`);
    if (!ok) return;
    await deleteDevice(deviceUid);
    await load();
  };

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDashboardState();
      setState(data);
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

  const openEdit = (item: {
    device_uid: string;
    description?: string | null;
    catalog_info?: string | null;
    location?: string | null;
  }) => {
    setEditingUid(item.device_uid);
    setEditDescription(item.description ?? "");
    setEditLocation(item.location ?? "");
    setEditCatalogInfo(item.catalog_info ?? "");
  };
  const closeEdit = () => {
    setEditingUid(null);
    setEditCatalogInfo("");
  };
  const saveEdit = async () => {
    if (!editingUid) return;
    try {
      await updateDeviceConfig(editingUid, {
        description: editDescription || null,
        location: editLocation || null,
        catalog_info: editCatalogInfo || null,
      });
      closeEdit();
      await load();
    } catch {
      // keep modal open on error
    }
  };

  const openFullInfo = (item: {
    device_uid: string;
    sensor_type?: string | null;
    actuator_type?: string | null;
    catalog_info?: string | null;
    description?: string | null;
    location?: string | null;
  }) => {
    const userText = (item.catalog_info ?? item.description ?? "").toString().trim();
    const title = item.sensor_type ?? item.actuator_type ?? "Устройство";
    const modelText = getDeviceModelText({
      sensor_type: item.sensor_type,
      actuator_type: item.actuator_type,
    });
    if (!userText && !modelText) return;
    setFullInfo({
      device_uid: item.device_uid,
      title,
      text: userText ? `${modelText}\n\n${userText}` : modelText,
      location: item.location ?? null,
    });
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
              <div
                key={s.device_uid}
                style={cardStyle}
                role="button"
                tabIndex={0}
                onClick={() =>
                  openFullInfo({
                    device_uid: s.device_uid,
                    sensor_type: s.sensor_type,
                    catalog_info: s.catalog_info,
                    description: s.description,
                    location: s.location,
                  })
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    openFullInfo({
                      device_uid: s.device_uid,
                      sensor_type: s.sensor_type,
                      catalog_info: s.catalog_info,
                      description: s.description,
                      location: s.location,
                    });
                  }
                }}
              >
                <div>
                  <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{s.device_uid}</div>
                  {(s.catalog_info || s.description) && (
                    <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                      {truncate(s.catalog_info ?? s.description, 95)}
                    </div>
                  )}
                  {s.location && (
                    <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                      {s.location}
                    </div>
                  )}
                  <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                    {s.sensor_type || "sensor"}: {s.value ?? "нет данных"}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                    {s.created_at ? new Date(s.created_at).toLocaleTimeString() : "нет данных"}
                  </span>
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEdit(s);
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
                      Изменить
                    </button>
                  )}
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteDevice(s.device_uid);
                      }}
                      style={{
                        padding: "0.25rem 0.5rem",
                        fontSize: "0.75rem",
                        borderRadius: 6,
                        border: "1px solid #ef4444",
                        background: "transparent",
                        color: "#fecaca",
                        cursor: "pointer",
                      }}
                    >
                      Удалить
                    </button>
                  )}
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
                  style={cardStyle}
                  role="button"
                  tabIndex={0}
                  onClick={() =>
                    openFullInfo({
                      device_uid: a.device_uid,
                      actuator_type: a.actuator_type,
                      catalog_info: a.catalog_info,
                      description: a.description,
                      location: a.location,
                    })
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      openFullInfo({
                        device_uid: a.device_uid,
                        actuator_type: a.actuator_type,
                        catalog_info: a.catalog_info,
                        description: a.description,
                        location: a.location,
                      });
                    }
                  }}
                >
                  <div>
                    <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>{a.device_uid}</div>
                    {(a.catalog_info || a.description) && (
                      <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                        {truncate(a.catalog_info ?? a.description, 95)}
                      </div>
                    )}
                    {a.location && (
                      <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: 2 }}>
                        {a.location}
                      </div>
                    )}
                    <div style={{ fontSize: "0.95rem", fontWeight: 500 }}>
                      {a.actuator_type}:{" "}
                      <span
                        style={{
                          color: a.state === "ON" ? "#bbf7d0" : a.state ? "#fca5a5" : "#fde68a",
                          fontWeight: 600,
                        }}
                      >
                        {a.state ?? "нет связи"}
                      </span>
                    </div>
                    <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#9ca3af" }}>
                      Режим:{" "}
                      {a.control_mode ? (
                        <strong style={{ color: a.control_mode === "AUTO" ? "#bfdbfe" : "#fde68a" }}>
                          {a.control_mode === "AUTO" ? "Авто" : "Ручной"}
                        </strong>
                      ) : (
                        <span style={{ color: "#6b7280" }}>нет данных</span>
                      )}
                    </div>
                  </div>
                  {isAdmin && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", alignItems: "flex-end" }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActuatorMode(
                            a.device_uid,
                            a.control_mode === "AUTO" ? "MANUAL" : "AUTO"
                          ).then(load);
                        }}
                        disabled={!a.control_mode}
                        style={{
                          padding: "0.25rem 0.6rem",
                          fontSize: "0.75rem",
                          borderRadius: 999,
                          border: "1px solid #374151",
                          background: "transparent",
                          color: !a.control_mode ? "#4b5563" : "#9ca3af",
                          cursor: !a.control_mode ? "default" : "pointer",
                        }}
                      >
                        {!a.control_mode ? "Нет связи" : a.control_mode === "AUTO" ? "В ручной" : "В авто"}
                      </button>

                      {a.control_mode === "MANUAL" && (
                        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              controlActuator({
                                device_uid: a.device_uid,
                                actuator_type: a.actuator_type,
                                action: "ON",
                              }).then(load);
                            }}
                            style={{
                              padding: "0.25rem 0.6rem",
                              fontSize: "0.75rem",
                              borderRadius: 999,
                              border: "1px solid #374151",
                              background: "transparent",
                              color: "#bbf7d0",
                              cursor: "pointer",
                            }}
                          >
                            ВКЛ
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              controlActuator({
                                device_uid: a.device_uid,
                                actuator_type: a.actuator_type,
                                action: "OFF",
                              }).then(load);
                            }}
                            style={{
                              padding: "0.25rem 0.6rem",
                              fontSize: "0.75rem",
                              borderRadius: 999,
                              border: "1px solid #374151",
                              background: "transparent",
                              color: "#fecaca",
                              cursor: "pointer",
                            }}
                          >
                            ВЫКЛ
                          </button>
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEdit(a);
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
                        Изменить описание
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteDevice(a.device_uid);
                        }}
                        style={{
                          padding: "0.25rem 0.5rem",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid #ef4444",
                          background: "transparent",
                          color: "#fecaca",
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
          )}
        </section>
      </div>

      {editingUid && (
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
          onClick={closeEdit}
        >
          <div
            style={{
              background: "#0f172a",
              padding: "1.5rem",
              borderRadius: 16,
              border: "1px solid #1f2937",
              minWidth: 320,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>
              Конфигурация: {editingUid}
            </h3>
            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                Описание
              </label>
              <input
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  borderRadius: 8,
                  border: "1px solid #1f2937",
                  background: "#020617",
                  color: "#e5e7eb",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                Полное описание (справочник)
              </label>
              <textarea
                value={editCatalogInfo}
                onChange={(e) => setEditCatalogInfo(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  borderRadius: 8,
                  border: "1px solid #1f2937",
                  background: "#020617",
                  color: "#e5e7eb",
                  boxSizing: "border-box",
                  minHeight: 120,
                }}
              />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                Место установки
              </label>
              <input
                value={editLocation}
                onChange={(e) => setEditLocation(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  borderRadius: 8,
                  border: "1px solid #1f2937",
                  background: "#020617",
                  color: "#e5e7eb",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={closeEdit}
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
              <button
                type="button"
                onClick={saveEdit}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: 8,
                  border: "none",
                  background: "linear-gradient(90deg,#22c55e,#22d3ee)",
                  color: "#020617",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}

      {fullInfo && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
          }}
          onClick={() => setFullInfo(null)}
        >
          <div
            style={{
              background: "#0f172a",
              padding: "1.5rem",
              borderRadius: 16,
              border: "1px solid #1f2937",
              minWidth: 340,
              maxWidth: 720,
              width: "90%",
              maxHeight: "80vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: "0.75rem", fontSize: "1rem" }}>
              {fullInfo.title} — полное описание
            </h3>
            {fullInfo.location && (
              <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginBottom: "0.75rem" }}>
                Место установки: {fullInfo.location}
              </div>
            )}
            <div
              style={{
                whiteSpace: "pre-wrap",
                color: "#e5e7eb",
                fontSize: "0.9rem",
                lineHeight: 1.4,
              }}
            >
              {fullInfo.text}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button
                type="button"
                onClick={() => setFullInfo(null)}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: 8,
                  border: "1px solid #374151",
                  background: "transparent",
                  color: "#9ca3af",
                  cursor: "pointer",
                }}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

