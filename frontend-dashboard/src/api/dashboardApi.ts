import { apiClient } from "./apiClient";

export interface SensorState {
  device_uid: string;
  sensor_type: string | null;
  value: number;
  created_at: string;
}

export interface ActuatorState {
  device_uid: string;
  actuator_type: string;
  state: string;
}

export interface DashboardState {
  sensors: SensorState[];
  actuators: ActuatorState[];
}

export async function fetchDashboardState() {
  const { data } = await apiClient.get<DashboardState>("/dashboard/state");
  return data;
}

