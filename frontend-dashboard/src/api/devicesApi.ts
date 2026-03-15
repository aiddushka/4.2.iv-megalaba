import { apiClient } from "./apiClient";

export interface Device {
  id: number;
  device_uid: string;
  device_type: string;
  description?: string | null;
  status: string;
  location?: string | null;
}

export interface AssignDevicePayload {
  device_uid: string;
  location: string;
}

export async function fetchUnassignedDevices() {
  const { data } = await apiClient.get<Device[]>("/devices/unassigned");
  return data;
}

export async function assignDevice(payload: AssignDevicePayload) {
  const { data } = await apiClient.post<Device>("/devices/assign", payload);
  return data;
}

