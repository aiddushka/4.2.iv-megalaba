import { apiClient } from "./apiClient";

export interface SensorState {
  device_uid: string;
  sensor_type: string | null;
  value: number;
  created_at: string;
  description?: string | null;
  location?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  indicator?: "green" | "yellow" | "red" | "unknown";
}

export interface ActuatorState {
  device_uid: string;
  actuator_type: string;
  state: string;
  description?: string | null;
  location?: string | null;
}

export interface DashboardState {
  sensors: SensorState[];
  actuators: ActuatorState[];
  links: {
    id: number;
    source_device_uid: string;
    target_device_uid: string;
    controller?: string | null;
    description?: string | null;
    active: boolean;
    auto_control_enabled?: boolean;
    min_value?: number | null;
    max_value?: number | null;
  }[];
}

export async function fetchDashboardState() {
  const { data } = await apiClient.get<DashboardState>("/dashboard/state");
  return data;
}

