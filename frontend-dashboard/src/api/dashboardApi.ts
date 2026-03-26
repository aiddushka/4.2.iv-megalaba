import { apiClient } from "./apiClient";

export interface SensorState {
  device_uid: string;
  sensor_type: string | null;
  value: number | null;
  created_at: string | null;
  description?: string | null;
  location?: string | null;
}

export interface ActuatorState {
  device_uid: string;
  actuator_type: string;
  state: string | null;
  description?: string | null;
  location?: string | null;
  control_mode: "AUTO" | "MANUAL" | null;
}

export interface DashboardState {
  sensors: SensorState[];
  actuators: ActuatorState[];
}

export async function fetchDashboardState() {
  const { data } = await apiClient.get<DashboardState>("/dashboard/state");
  return data;
}

