import { FormEvent, useState } from "react";

export interface DeviceFormValues {
  device_uid: string;
  device_type: string;
  description?: string;
  location_hint?: string;
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
  });
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!values.device_uid.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(values);
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

  return (
    <form onSubmit={handleSubmit}>
      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="device_uid">
          UID устройства
        </label>
        <input
          id="device_uid"
          name="device_uid"
          style={inputStyle}
          value={values.device_uid}
          onChange={handleChange}
          placeholder="например, temp_sensor_1"
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
          <option value="HEATER_ACTUATOR">Актуатор обогрева</option>
          <option value="VENTILATION_ACTUATOR">Актуатор вентиляции</option>
          <option value="LIGHT_ACTUATOR">Актуатор освещения</option>
        </select>
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="description">
          Описание
        </label>
        <textarea
          id="description"
          name="description"
          style={{ ...inputStyle, minHeight: 60 }}
          value={values.description}
          onChange={handleChange}
          placeholder="например, Датчик температуры в центре теплицы"
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle} htmlFor="location_hint">
          Планируемое место установки
        </label>
        <input
          id="location_hint"
          name="location_hint"
          style={inputStyle}
          value={values.location_hint}
          onChange={handleChange}
          placeholder="например, Теплица А, левая грядка"
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
