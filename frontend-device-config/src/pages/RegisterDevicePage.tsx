import { useState } from "react";
import { DeviceFormValues, DeviceForm } from "../components/DeviceForm";
import { registerDevice } from "../api/devicesApi";

export function RegisterDevicePage() {
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: DeviceFormValues) => {
    setResult(null);
    setError(null);
    try {
      const data = await registerDevice({
        device_uid: values.device_uid,
        device_type: values.device_type,
        description: values.description,
        location_hint: values.location_hint,
        controller: values.controller,
        pin: Number(values.pin),
        bus: values.bus,
        bus_address: values.bus_address || undefined,
        components: values.components.length ? values.components : undefined,
      });
      setResult(`Устройство зарегистрировано: id=${data.id}, status=${data.status}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Ошибка при регистрации устройства");
    }
  };

  return (
    <div
      style={{
        maxWidth: 520,
        margin: "0 auto",
        padding: "2rem",
        background: "#020617",
        borderRadius: 16,
        boxShadow: "0 25px 50px -12px rgba(15,23,42,0.8)",
      }}
    >
      <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        Регистрация устройства
      </h2>
      <p style={{ marginBottom: "1.5rem", color: "#9ca3af", fontSize: "0.9rem" }}>
        Представь, что ты работаешь с «ноутбука/флешки», подключённой к устройству. Здесь ты
        создаёшь запись об устройстве в системе, чтобы администратор мог потом увидеть его на
        основном сайте и «установить на доску».
      </p>
      <DeviceForm onSubmit={handleSubmit} />
      {result && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            background: "rgba(22,163,74,0.15)",
            color: "#bbf7d0",
            fontSize: "0.9rem",
          }}
        >
          {result}
        </div>
      )}
      {error && (
        <div
          style={{
            marginTop: "1rem",
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
    </div>
  );
}

