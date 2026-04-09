import { Device } from "../api/devicesApi";

interface Props {
  device: Device;
}

export function DeviceInfoBlock({ device }: Props) {
  const sectionStyle: React.CSSProperties = {
    border: "1px solid #1f2937",
    borderRadius: 12,
    background: "#020617",
    padding: "1rem",
    marginBottom: "0.75rem",
  };

  const labelStyle: React.CSSProperties = {
    color: "#9ca3af",
    fontSize: "0.8rem",
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
  const imageName = imageByDeviceType[device.device_type] || "AUno_датчик_температуры.png";
  const previewUrl = `http://localhost:8000/static/images/ArduinoUnoComponents/${encodeURIComponent(imageName)}`;
  const rowStyle: React.CSSProperties = { borderBottom: "1px solid #1f2937" };
  const tdStyle: React.CSSProperties = { padding: "0.4rem 0.5rem", fontSize: "0.85rem" };

  return (
    <div>
      <div style={sectionStyle}>
        <h4 style={{ margin: "0 0 0.75rem 0", color: "#22d3ee" }}>Основная информация</h4>
        <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
          <img
            src={previewUrl}
            alt={device.device_type}
            width={86}
            height={86}
            style={{ borderRadius: 8, border: "1px solid #1f2937", objectFit: "cover", background: "#0f172a" }}
            onError={(e) => {
              const target = e.currentTarget;
              target.onerror = null;
              target.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='86' height='86'><rect width='100%' height='100%' fill='%230f172a'/><text x='50%' y='54%' text-anchor='middle' fill='%239ca3af' font-size='12' font-family='Arial'>No image</text></svg>";
            }}
          />
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <tr style={rowStyle}><td style={tdStyle}>UID</td><td style={tdStyle}>{device.device_uid}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Тип</td><td style={tdStyle}>{device.device_type}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Контроллер</td><td style={tdStyle}>{device.controller || "не указан"}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Pin</td><td style={tdStyle}>{device.pin ?? "не указан"}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Шина</td><td style={tdStyle}>{device.bus || "не указана"}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>I2C адрес</td><td style={tdStyle}>{device.bus_address || "не указан"}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Компоненты</td><td style={tdStyle}>{device.components?.length ? device.components.join(", ") : "не указаны"}</td></tr>
              <tr style={rowStyle}><td style={tdStyle}>Описание</td><td style={tdStyle}>{device.description || "Описание отсутствует"}</td></tr>
              <tr><td style={tdStyle}>Место установки</td><td style={tdStyle}>{device.location || "не указано"}</td></tr>
            </tbody>
          </table>
        </div>
        <div style={{ ...labelStyle, marginTop: "0.5rem" }}>Статическое изображение: {imageName}</div>
      </div>
    </div>
  );
}
