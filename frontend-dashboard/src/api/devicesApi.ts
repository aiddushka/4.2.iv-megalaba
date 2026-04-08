import { apiClient } from "./apiClient";

export interface Device {
  id: number;
  device_uid: string;
  device_type: string;
  description?: string | null;
  controller?: string | null;
  pin?: number | null;
  bus?: string | null;
  bus_address?: string | null;
  components?: string[] | null;
  status: string;
  location?: string | null;
  last_maintenance?: string | null;
  maintenance_notes?: string | null;
  change_history?:
    | {
        timestamp: string;
        field: string;
        old_value?: string | number | null;
        new_value?: string | number | null;
        changed_by?: string | null;
      }[]
    | null;
}

export interface AssignDevicePayload {
  device_uid: string;
  location: string;
}

export async function fetchUnassignedDevices() {
  const { data } = await apiClient.get<Device[]>("/devices/unassigned");
  return data;
}

export async function fetchAssignedDevices() {
  const { data } = await apiClient.get<Device[]>("/devices/assigned");
  return data;
}

export async function assignDevice(payload: AssignDevicePayload) {
  const { data } = await apiClient.post<Device>("/devices/assign", payload);
  return data;
}

export interface RegisterDevicePayload {
  device_uid: string;
  device_type: string;
  description?: string;
  location_hint?: string;
}

export async function registerDevice(payload: RegisterDevicePayload) {
  const { data } = await apiClient.post<Device>("/devices/register", payload);
  return data;
}

export interface UpdateDevicePayload {
  description?: string | null;
  location?: string | null;
  status?: string | null;
  last_maintenance?: string | null;
  maintenance_notes?: string | null;
}

export async function updateDeviceConfig(
  deviceUid: string,
  payload: UpdateDevicePayload
) {
  const { data } = await apiClient.patch<Device>(
    `/devices/${encodeURIComponent(deviceUid)}`,
    payload
  );
  return data;
}

export async function fetchDeviceByUid(deviceUid: string) {
  const { data } = await apiClient.get<Device>(`/devices/${encodeURIComponent(deviceUid)}`);
  return data;
}

