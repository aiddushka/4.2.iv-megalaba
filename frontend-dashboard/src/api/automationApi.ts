import { apiClient } from "./apiClient";

export interface DeviceLink {
  id: number;
  source_device_uid: string;
  target_device_uid: string;
  controller?: string | null;
  description?: string | null;
  active: boolean;
}

export interface CreateDeviceLinkPayload {
  source_device_uid: string;
  target_device_uid: string;
  controller?: string;
  description?: string;
  active?: boolean;
}

export async function createDeviceLink(payload: CreateDeviceLinkPayload) {
  const { data } = await apiClient.post<DeviceLink>("/automation/links", payload);
  return data;
}

export async function deleteDeviceLink(linkId: number) {
  const { data } = await apiClient.delete<{ ok: boolean }>(`/automation/links/${linkId}`);
  return data;
}
