import { apiClient } from "./apiClient";

export interface ActuatorCommandPayload {
  device_uid: string;
  actuator_type?: string;
  action: "ON" | "OFF";
}

export async function controlActuator(payload: ActuatorCommandPayload) {
  const { data } = await apiClient.post("/actuators/control", payload);
  return data;
}
