import { apiClient } from "./apiClient";

export interface SensorState {
  device_uid: string;
  sensor_type: string | null;
  value: number | null;
  created_at: string | null;
  description?: string | null;
  catalog_info?: string | null;
  location?: string | null;
  model_name?: string | null;
  manufacturer?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  is_configured?: boolean | null;
  config_settings?: Record<string, any> | null;
}

export interface ActuatorState {
  device_uid: string;
  actuator_type: string;
  state: string | null;
  description?: string | null;
  catalog_info?: string | null;
  location?: string | null;
  control_mode: "AUTO" | "MANUAL" | null;
  model_name?: string | null;
  manufacturer?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  is_configured?: boolean | null;
  config_settings?: Record<string, any> | null;
}

export interface DashboardState {
  sensors: SensorState[];
  actuators: ActuatorState[];
}

export async function fetchDashboardState() {
  const { data } = await apiClient.get<DashboardState>("/dashboard/state");
  return data;
}

