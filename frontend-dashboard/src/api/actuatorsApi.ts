import { apiClient } from "./apiClient";

export async function setActuatorMode(
  deviceUid: string,
  controlMode: "AUTO" | "MANUAL"
) {
  const { data } = await apiClient.patch(`/actuators/${encodeURIComponent(deviceUid)}/mode`, {
    control_mode: controlMode,
  });
  return data;
}

export async function controlActuator(params: {
  device_uid: string;
  action: "ON" | "OFF";
  actuator_type?: string;
}) {
  const { data } = await apiClient.post("/actuators/control", params);
  return data;
}

