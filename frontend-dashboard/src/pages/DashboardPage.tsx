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
  const [editModelName, setEditModelName] = useState("");
  const [editManufacturer, setEditManufacturer] = useState("");
  const [editMinValue, setEditMinValue] = useState<string>("");
  const [editMaxValue, setEditMaxValue] = useState<string>("");
  const [editIsConfigured, setEditIsConfigured] = useState<boolean>(false);
  const [editConfigSettings, setEditConfigSettings] = useState<string>("");

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
    value?: number | null;
    state?: string | null;
    model_name?: string | null;
    manufacturer?: string | null;
    min_value?: number | null;
    max_value?: number | null;
  }) => {
    const sensorType = (args.sensor_type ?? "").toUpperCase();
    const actuatorType = (args.actuator_type ?? "").toUpperCase();
    const modelName = (args.model_name ?? "").trim();
    const manufacturer = (args.manufacturer ?? "").trim();
    const minValue = args.min_value ?? null;
    const maxValue = args.max_value ?? null;

    const userModelBlock = (fallbackModel: string, fallbackManufacturer: string) => {
      const m = modelName || fallbackModel;
      const manuf = manufacturer || fallbackManufacturer;
      return `Модель: ${m}\nПроизводитель: ${manuf}`;
    };

    if (sensorType === "TEMP_SENSOR") {
      return (
        `Название: Температура воздуха (датчик)\n` +
        `Тип устройства: ${sensorType}\n` +
        `Текущее значение: ${args.value ?? "нет данных"} °C\n\n` +
        `${userModelBlock("DHT22 / DS18B20", "AOSONG / Maxim Integrated")}\n\n` +
        `Технические характеристики: точность ±0.5°C\n` +
        `Единицы измерения: °C\n` +
        `Диапазон работы: -40°C … +80°C\n` +
        `Оптимальный диапазон для теплицы: 18°C … 25°C\n\n` +
        `Назначение: контроль микроклимата, управление обогревом и вентиляцией.\n\n` +
        `Модель работы (эмулятор): температура задаётся суточным циклом ` +
        `T(t)=T0 + A*sin(2πt/24h) + шум + медленный дрейф.`
      );
    }
    if (sensorType === "HUMIDITY_AIR_SENSOR") {
      return (
        `Название: Влажность воздуха (датчик)\n` +
        `Тип устройства: ${sensorType}\n` +
        `Текущее значение: ${args.value ?? "нет данных"} %\n\n` +
        `${userModelBlock("DHT22 / AM2302", "AOSONG")}\n\n` +
        `Технические характеристики: точность ±2%\n` +
        `Единицы измерения: %\n` +
        `Диапазон работы: 0% … 100%\n` +
        `Оптимальный диапазон для теплицы: 40% … 70%\n\n` +
        `Назначение: контроль микроклимата, снижение риска грибковых заболеваний.\n\n` +
        `Модель работы (эмулятор): влажность меняется в противофазе к температуре ` +
        `(днём суше, ночью влажнее) + гауссовский шум.`
      );
    }
    if (sensorType === "HUMIDITY_SOIL_SENSOR") {
      return (
        `Название: Влажность почвы (датчик)\n` +
        `Тип устройства: ${sensorType}\n` +
        `Текущее значение: ${args.value ?? "нет данных"} %\n\n` +
        `${userModelBlock("YL-69 / HL-69", "Seeed Studio")}\n\n` +
        `Технические характеристики: точность ±5%\n` +
        `Единицы измерения: %\n` +
        `Диапазон работы: 0% … 100%\n` +
        `Оптимальный диапазон для теплицы: 50% … 80%\n\n` +
        `Назначение: автоматический полив, предотвращение пересыхания грунта.\n\n` +
        `Модель работы (эмулятор): влажность убывает из-за испарения, ` +
        `редко происходят «поливы» (скачки влажности), плюс шум датчика.`
      );
    }
    if (sensorType === "LIGHT_SENSOR") {
      return (
        `Название: Освещённость (датчик)\n` +
        `Тип устройства: ${sensorType}\n` +
        `Текущее значение: ${args.value ?? "нет данных"} lx\n\n` +
        `${userModelBlock("BH1750 / GY-30", "Rohm Semiconductor")}\n\n` +
        `Технические характеристики: точность ±20%\n` +
        `Единицы измерения: люкс (lx)\n` +
        `Диапазон работы: 1 … 65535 lx\n` +
        `Оптимальный диапазон для растений: 10000 … 50000 lx\n\n` +
        `Назначение: управление дополнительным освещением, контроль светового дня.\n\n` +
        `Модель работы (эмулятор): освещённость задаётся функцией времени суток ` +
        `с дневным максимумом и редкими «провалами» (условные «облака») + шум.`
      );
    }

    if (actuatorType === "IRRIGATION_ACTUATOR") {
      return (
        `Название: Система полива (актуатор)\n` +
        `Тип устройства: ${actuatorType}\n` +
        `Текущее состояние: ${args.state ?? "нет данных"}\n\n` +
        `${userModelBlock("Solenoid Valve 3/4\" / Drip Irrigation Kit", "Hunter / Rain Bird")}\n\n` +
        `Назначение: поддержание оптимальной влажности почвы.\n` +
        `Технические характеристики: 12V DC / 24V AC, до ~50 л/мин (зависит от комплекта)\n` +
        `Управление в проекте: ON/OFF (в демо — ограниченное время работы при включении)\n\n` +
        `Модель работы (эмулятор): при команде ON устройство включает полив на ограниченное время, затем OFF.`
      );
    }
    if (actuatorType === "HEATER_ACTUATOR") {
      return (
        `Название: Обогреватель/подогрев (актуатор)\n` +
        `Тип устройства: ${actuatorType}\n` +
        `Текущее состояние: ${args.state ?? "нет данных"}\n\n` +
        `${userModelBlock("Infrared Heater / Heat Mat", "Biogreen / HeatMat")}\n\n` +
        `Назначение: поддержание температуры воздуха и почвы в холодное время.\n` +
        `Технические характеристики: 220V AC, 500W … 2000W, защита IP44 (пример)\n` +
        `Управление в проекте: ON/OFF\n\n` +
        `Модель работы (эмулятор): при команде ON подогрев работает ограниченное время (тепловая инерция), затем OFF.`
      );
    }
    if (actuatorType === "VENTILATION_ACTUATOR") {
      return (
        `Название: Вентиляция (актуатор)\n` +
        `Тип устройства: ${actuatorType}\n` +
        `Текущее состояние: ${args.state ?? "нет данных"}\n\n` +
        `${userModelBlock("Axial Fan / Exhaust Fan", "VENTS / Soler & Palau")}\n\n` +
        `Назначение: циркуляция и обновление воздуха.\n` +
        `Технические характеристики (типовые): производительность до 1000 м³/час, шум < 35 дБ\n` +
        `Режимы (концептуально): приточная/вытяжная/рециркуляция\n` +
        `Управление в проекте: ON/OFF\n\n` +
        `Модель работы (эмулятор): при команде ON вентиляция включается на ограниченный интервал, затем OFF.`
      );
    }
    if (actuatorType === "LIGHT_ACTUATOR") {
      return (
        `Название: Освещение (актуатор)\n` +
        `Тип устройства: ${actuatorType}\n` +
        `Текущее состояние: ${args.state ?? "нет данных"}\n\n` +
        `${userModelBlock("Full Spectrum LED Grow Light", "Spider Farmer / Mars Hydro")}\n\n` +
        `Назначение: досвечивание растений и управление световым днём.\n` +
        `Технические характеристики: 400–700 нм (PAR), 100W … 600W, высота подвеса 30–100 см\n` +
        `Управление в проекте: ON/OFF\n\n` +
        `Модель работы (эмулятор): освещение переключается по ON/OFF и сразу публикует статус.`
      );
    }

    return "Паспорт устройства: поведение зависит от типа (датчик/актуатор).";
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
    model_name?: string | null;
    manufacturer?: string | null;
    min_value?: number | null;
    max_value?: number | null;
    is_configured?: boolean | null;
    config_settings?: Record<string, any> | null;
    location?: string | null;
  }) => {
    setEditingUid(item.device_uid);
    setEditDescription(item.description ?? "");
    setEditLocation(item.location ?? "");
    setEditCatalogInfo(item.catalog_info ?? "");
    setEditModelName(item.model_name ?? "");
    setEditManufacturer(item.manufacturer ?? "");
    setEditMinValue(item.min_value !== null && item.min_value !== undefined ? String(item.min_value) : "");
    setEditMaxValue(item.max_value !== null && item.max_value !== undefined ? String(item.max_value) : "");
    setEditIsConfigured(Boolean(item.is_configured));
    setEditConfigSettings(
      item.config_settings ? JSON.stringify(item.config_settings, null, 2) : ""
    );
  };
  const closeEdit = () => {
    setEditingUid(null);
    setEditCatalogInfo("");
    setEditDescription("");
    setEditLocation("");
    setEditModelName("");
    setEditManufacturer("");
    setEditMinValue("");
    setEditMaxValue("");
    setEditIsConfigured(false);
    setEditConfigSettings("");
  };
  const saveEdit = async () => {
    if (!editingUid) return;
    try {
      let parsedConfigSettings: Record<string, any> | null = null;
      if (editConfigSettings.trim()) {
        try {
          parsedConfigSettings = JSON.parse(editConfigSettings);
        } catch {
          parsedConfigSettings = null;
        }
      }
      await updateDeviceConfig(editingUid, {
        description: editDescription || null,
        location: editLocation || null,
        catalog_info: editCatalogInfo || null,
        model_name: editModelName || null,
        manufacturer: editManufacturer || null,
        min_value: editMinValue.trim() ? Number(editMinValue) : null,
        max_value: editMaxValue.trim() ? Number(editMaxValue) : null,
        is_configured: editIsConfigured,
        config_settings: parsedConfigSettings,
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
    value?: number | null;
    state?: string | null;
    model_name?: string | null;
    manufacturer?: string | null;
    min_value?: number | null;
    max_value?: number | null;
  }) => {
    const userText = (item.catalog_info ?? item.description ?? "").toString().trim();
    const title = item.sensor_type ?? item.actuator_type ?? "Устройство";
    const modelText = getDeviceModelText({
      sensor_type: item.sensor_type,
      actuator_type: item.actuator_type,
      value: item.value ?? null,
      state: item.state ?? null,
      model_name: item.model_name,
      manufacturer: item.manufacturer,
      min_value: item.min_value,
      max_value: item.max_value,
    });
    if (!userText && !modelText) return;
    setFullInfo({
      device_uid: item.device_uid,
      title,
      text: userText ? `${modelText}\n\nПользовательская справка:\n${userText}` : modelText,
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
                    value: s.value ?? null,
                    model_name: s.model_name ?? null,
                    manufacturer: s.manufacturer ?? null,
                    min_value: s.min_value ?? null,
                    max_value: s.max_value ?? null,
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
                      value: s.value ?? null,
                      model_name: s.model_name ?? null,
                      manufacturer: s.manufacturer ?? null,
                      min_value: s.min_value ?? null,
                      max_value: s.max_value ?? null,
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
                  {s.is_configured === false && (
                    <div style={{ marginTop: 6, fontSize: "0.75rem", color: "#fecaca" }}>
                      Не настроено
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
                      state: a.state ?? null,
                      model_name: a.model_name ?? null,
                      manufacturer: a.manufacturer ?? null,
                      min_value: a.min_value ?? null,
                      max_value: a.max_value ?? null,
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
                        state: a.state ?? null,
                        model_name: a.model_name ?? null,
                        manufacturer: a.manufacturer ?? null,
                        min_value: a.min_value ?? null,
                        max_value: a.max_value ?? null,
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
                    {a.is_configured === false && (
                      <div style={{ marginTop: 6, fontSize: "0.75rem", color: "#fecaca" }}>
                        Не настроено
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

            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                Модель устройства
              </label>
              <input
                value={editModelName}
                onChange={(e) => setEditModelName(e.target.value)}
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
                Производитель
              </label>
              <input
                value={editManufacturer}
                onChange={(e) => setEditManufacturer(e.target.value)}
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

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                  min_value
                </label>
                <input
                  value={editMinValue}
                  onChange={(e) => setEditMinValue(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: 8,
                    border: "1px solid #1f2937",
                    background: "#020617",
                    color: "#e5e7eb",
                    boxSizing: "border-box",
                  }}
                  placeholder="например, 15"
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                  max_value
                </label>
                <input
                  value={editMaxValue}
                  onChange={(e) => setEditMaxValue(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    borderRadius: 8,
                    border: "1px solid #1f2937",
                    background: "#020617",
                    color: "#e5e7eb",
                    boxSizing: "border-box",
                  }}
                  placeholder="например, 30"
                />
              </div>
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={editIsConfigured}
                  onChange={(e) => setEditIsConfigured(e.target.checked)}
                />
                <span style={{ color: "#9ca3af", fontSize: "0.9rem" }}>
                  Устройство настроено
                </span>
              </label>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: 4 }}>
                config_settings (JSON)
              </label>
              <textarea
                value={editConfigSettings}
                onChange={(e) => setEditConfigSettings(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  borderRadius: 8,
                  border: "1px solid #1f2937",
                  background: "#020617",
                  color: "#e5e7eb",
                  boxSizing: "border-box",
                  minHeight: 100,
                }}
                placeholder='например: {"calibration_offset": 0.2, "frequency_seconds": 5}'
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

