import { FormEvent, useState } from "react";

export interface DeviceFormValues {
  device_uid: string;
  device_type: string;
  description: string;
  location_hint: string;
  controller: string;
  pin: number | "";
  bus: string;
  bus_address: string;
  components: string[];
  linked_device_uid: string;
  link_description: string;
}

interface Props {
  onSubmit: (values: DeviceFormValues) => void | Promise<void>;
}

export function DeviceForm({ onSubmit }: Props) {
  const [values, setValues] = useState<DeviceFormValues>({
    device_uid: "",
    device_type: "TEMP_SENSOR",
    description: "",
    location_hint: "",
    controller: "Arduino Uno",
    pin: "",
    bus: "Digital",
    bus_address: "",
    components: [],
    linked_device_uid: "",
    link_description: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const getDeviceTypeLabel = (type: string) => {
    switch (type) {
      case "TEMP_SENSOR":
        return "Датчик температуры";
      case "HUMIDITY_AIR_SENSOR":
        return "Датчик влажности воздуха";
      case "HUMIDITY_SOIL_SENSOR":
        return "Датчик влажности почвы";
      case "LIGHT_SENSOR":
        return "Датчик освещённости";
      case "IRRIGATION_ACTUATOR":
        return "Актуатор полива";
      case "HEATER_ACTUATOR":
        return "Актуатор температуры";
      case "VENTILATION_ACTUATOR":
        return "Актуатор вентиляции";
      case "LIGHT_ACTUATOR":
        return "Актуатор освещения";
      default:
        return "Устройство";
    }
  };

  const buildDescriptionText = (currentValues: DeviceFormValues) => {
    const kind = getDeviceTypeLabel(currentValues.device_type);
    const pinLabel = currentValues.pin === "" ? "указанному GPIO пину" : `GPIO пину ${currentValues.pin}`;
    const componentsLabel =
      currentValues.components.length > 0 ? currentValues.components.join(", ") : "выбранным компонентам";

    const busDetails =
      currentValues.bus === "I2C"
        ? `по шине I2C${currentValues.bus_address.trim() ? ` (адрес ${currentValues.bus_address.trim()})` : ""}`
        : `по шине ${currentValues.bus}`;

    if (currentValues.device_type.includes("ACTUATOR")) {
      return `${kind} управляется через ${currentValues.controller}, подключён к ${pinLabel} ${busDetails} с использованием компонентов ${componentsLabel}. Логика срабатывания определяется сценарием управления.`;
    }

    return `${kind} подключён к ${pinLabel} контроллера ${currentValues.controller} ${busDetails}. Используются компоненты: ${componentsLabel}. Измерения выполняются по расписанию системы.`;
  };
  const generatedDescription = buildDescriptionText(values);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    if (name === "pin") {
      setValues((prev) => ({ ...prev, pin: value === "" ? "" : Number(value) }));
      return;
    }
    if (name === "bus") {
      setValues((prev) => ({ ...prev, bus: value, bus_address: value === "I2C" ? prev.bus_address : "" }));
      return;
    }
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const handleComponentsChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = Array.from(e.target.selectedOptions).map((option) => option.value);
    setValues((prev) => ({ ...prev, components: selected }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!values.device_uid.trim()) return;
    if (values.pin === "") return;
    setSubmitting(true);
    try {
      await onSubmit({
        ...values,
        description: values.description.trim() || generatedDescription,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const fieldStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    marginBottom: "1rem",
  };

  const inputStyle: React.CSSProperties = {
    padding: "0.5rem 0.75rem",
    borderRadius: 8,
    border: "1px solid #1f2937",
    background: "#020617",
    color: "#e5e7eb",
    fontSize: "0.9rem",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.85rem",
    color: "#9ca3af",
  };
  const imageByDeviceType: Record<string, string> = {
    TEMP_SENSOR: "AUno_датчик_температуры.png",
    HUMIDITY_AIR_SENSOR: "AUno_датчик_влажности_почвы.png",
    HUMIDITY_SOIL_SENSOR: "AUno_датчик_влажности_почвы.png",
    LIGHT_SENSOR: "AUno_датчик_освещенности.png",
    IRRIGATION_ACTUATOR: "AUno_Актуатор_полив_с_мотором.png",
    HEATER_ACTUATOR: "AUno_прогревательный_элемент.png",
    VENTILATION_ACTUATOR: "AUno_актуатор_вентеляции.png",
    LIGHT_ACTUATOR: "AUno_актуратор_освещения.png",
  };
  const previewImageName = imageByDeviceType[values.device_type] || "AUno_датчик_температуры.png";
  const previewUrl = `http://localhost:8000/static/images/ArduinoUnoComponents/${encodeURIComponent(previewImageName)}`;

  return (
    <form onSubmit={handleSubmit}>
      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="device_uid">
          *UID устройства (поле обязательно для заполнения)
        </label>
        <input
          id="device_uid"
          name="device_uid"
          style={inputStyle}
          value={values.device_uid}
          onChange={handleChange}
          placeholder="например, controller_1"
          required
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="device_type">
          Тип устройства
        </label>
        <select
          id="device_type"
          name="device_type"
          style={inputStyle}
          value={values.device_type}
          onChange={handleChange}
        >
          <option value="TEMP_SENSOR">Датчик температуры</option>
          <option value="HUMIDITY_AIR_SENSOR">Датчик влажности воздуха</option>
          <option value="HUMIDITY_SOIL_SENSOR">Датчик влажности почвы</option>
          <option value="LIGHT_SENSOR">Датчик освещённости</option>
          <option value="IRRIGATION_ACTUATOR">Актуатор полива</option>
          <option value="HEATER_ACTUATOR">Актуатор температуры</option>
          <option value="VENTILATION_ACTUATOR">Актуатор вентиляции</option>
          <option value="LIGHT_ACTUATOR">Актуатор освещения</option>
        </select>
        <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <img
            src={previewUrl}
            alt={values.device_type}
            width={50}
            height={50}
            style={{ borderRadius: 6, border: "1px solid #1f2937", objectFit: "cover", background: "#0f172a" }}
            onError={(e) => {
              const target = e.currentTarget;
              target.onerror = null;
              target.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='50' height='50'><rect width='100%' height='100%' fill='%230f172a'/><text x='50%' y='54%' text-anchor='middle' fill='%239ca3af' font-size='10' font-family='Arial'>No image</text></svg>";
            }}
          />
          <span style={{ color: "#9ca3af", fontSize: "0.8rem" }}>Превью устройства</span>
        </div>
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="controller">
          Контроллер
        </label>
        <select
          id="controller"
          name="controller"
          style={inputStyle}
          value={values.controller}
          onChange={handleChange}
          required
        >
          <option value="Arduino Uno">Arduino Uno</option>
          <option value="Arduino Nano">Arduino Nano</option>
          <option value="ESP32">ESP32</option>
          <option value="Raspberry Pi">Raspberry Pi</option>
        </select>
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="pin">
          *Pin GPIO (поле обязательно для заполнения)
        </label>
        <input
          id="pin"
          name="pin"
          type="number"
          min={0}
          style={inputStyle}
          value={values.pin}
          onChange={handleChange}
          placeholder="например, 2"
          required
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="bus">
          Шина подключения
        </label>
        <select id="bus" name="bus" style={inputStyle} value={values.bus} onChange={handleChange} required>
          <option value="Digital">Digital</option>
          <option value="Analog">Analog</option>
          <option value="I2C">I2C</option>
          <option value="SPI">SPI</option>
          <option value="OneWire">OneWire</option>
        </select>
      </div>

      {values.bus === "I2C" && (
        <div style={fieldStyle}>
          <label style={labelStyle} htmlFor="bus_address">
            I2C адрес
          </label>
          <input
            id="bus_address"
            name="bus_address"
            style={inputStyle}
            value={values.bus_address}
            onChange={handleChange}
            placeholder="например, 0x76"
          />
        </div>
      )}

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="components">
          Компоненты
        </label>
        <select
          id="components"
          name="components"
          style={{ ...inputStyle, minHeight: 120 }}
          multiple
          value={values.components}
          onChange={handleComponentsChange}
        >
          <option value="DHT22">DHT22</option>
          <option value="DS18B20">DS18B20</option>
          <option value="BH1750">BH1750</option>
          <option value="Резистор 10кОм">Резистор 10кОм</option>
          <option value="Реле">Реле</option>
          <option value="Транзистор">Транзистор</option>
          <option value="Конденсатор">Конденсатор</option>
        </select>
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="description">
          Описание
        </label>
        <textarea
          id="description"
          name="description"
          style={{ ...inputStyle, minHeight: 120 }}
          value={values.description}
          onChange={handleChange}
          placeholder={generatedDescription}
          rows={6}
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="location_hint">
          *Планируемое место установки (поле обязательно для заполнения)
        </label>
        <input
          id="location_hint"
          name="location_hint"
          style={inputStyle}
          value={values.location_hint}
          onChange={handleChange}
          placeholder="например, Теплица А, левая грядка"
          required
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="linked_device_uid">
          Связать с устройством (UID, опционально)
        </label>
        <input
          id="linked_device_uid"
          name="linked_device_uid"
          style={inputStyle}
          value={values.linked_device_uid}
          onChange={handleChange}
          placeholder={
            values.device_type.includes("ACTUATOR")
              ? "UID датчика, который управляет этим актуатором"
              : "UID актуатора, которым управляет этот датчик"
          }
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="link_description">
          Комментарий к связи (опционально)
        </label>
        <input
          id="link_description"
          name="link_description"
          style={inputStyle}
          value={values.link_description}
          onChange={handleChange}
          placeholder="например, полив включается при влажности почвы ниже порога"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        style={{
          width: "100%",
          padding: "0.6rem 0.75rem",
          borderRadius: 999,
          border: "none",
          background: submitting ? "#4b5563" : "linear-gradient(90deg,#22c55e,#22d3ee)",
          color: "#020617",
          fontWeight: 600,
          cursor: submitting ? "default" : "pointer",
          fontSize: "0.95rem",
        }}
      >
        {submitting ? "Сохраняем..." : "Зарегистрировать устройство"}
      </button>
    </form>
  );
}

