import { apiClient } from "./apiClient";

export interface RegisterDevicePayload {
  device_uid: string;
  device_type: string;
  description?: string;
  location_hint?: string;
  controller: string;
  pin: number;
  bus: string;
  bus_address?: string;
  components?: string[];
}

export async function registerDevice(payload: RegisterDevicePayload) {
  const { data } = await apiClient.post("/devices/register", payload);
  return data;
}

export interface PublicDeviceRow {
  device_uid: string;
  device_type: string;
  location: string | null;
  status: string;
  accepts_data: boolean;
  linked_device_uids: string[];
}

export async function fetchDevicesPublic() {
  const { data } = await apiClient.get<PublicDeviceRow[]>("/devices/public/list");
  return data;
}

export async function setDeviceRuntimePublic(deviceUid: string, status: "active" | "disabled") {
  const { data } = await apiClient.patch(
    `/devices/public/${encodeURIComponent(deviceUid)}/runtime`,
    { status },
  );
  return data;
}

export async function deleteDevicePublic(deviceUid: string) {
  const { data } = await apiClient.delete(`/devices/public/${encodeURIComponent(deviceUid)}`);
  return data;
}

