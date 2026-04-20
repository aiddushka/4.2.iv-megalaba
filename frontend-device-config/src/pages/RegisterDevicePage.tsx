import { useState } from "react";
import { DeviceFormValues, DeviceForm } from "../components/DeviceForm";
import { registerDevice } from "../api/devicesApi";
import { createDeviceLink } from "../api/automationApi";

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
      if (values.linked_device_uid.trim()) {
        const isActuator = values.device_type.includes("ACTUATOR");
        await createDeviceLink({
          source_device_uid: isActuator ? values.linked_device_uid.trim() : values.device_uid,
          target_device_uid: isActuator ? values.device_uid : values.linked_device_uid.trim(),
          controller: values.controller,
          description: values.link_description || undefined,
          active: true,
        });
      }
      setResult(
        `Устройство зарегистрировано: id=${data.id}, status=${data.status}\n` +
          `Токен устройства: ${data.device_token}`,
      );
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Ошибка при регистрации устройства");
    }
  };

  return (
    <div
      style={{
        maxWidth: 800,
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
            whiteSpace: "pre-wrap",
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

