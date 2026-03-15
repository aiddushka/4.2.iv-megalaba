import { apiClient } from "./apiClient";

export interface RegisterDevicePayload {
  device_uid: string;
  device_type: string;
  description?: string;
  location_hint?: string;
}

export async function registerDevice(payload: RegisterDevicePayload) {
  const { data } = await apiClient.post("/devices/register", payload);
  return data;
}

