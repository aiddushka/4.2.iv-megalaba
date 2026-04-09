import { apiClient } from "./apiClient";

export interface DeviceLink {
  id: number;
  source_device_uid: string;
  target_device_uid: string;
  controller?: string | null;
  description?: string | null;
  active: boolean;
  auto_control_enabled?: boolean;
  min_value?: number | null;
  max_value?: number | null;
}

export interface CreateDeviceLinkPayload {
  source_device_uid: string;
  target_device_uid: string;
  controller?: string;
  description?: string;
  active?: boolean;
  auto_control_enabled?: boolean;
  min_value?: number;
  max_value?: number;
}

export async function createDeviceLink(payload: CreateDeviceLinkPayload) {
  const { data } = await apiClient.post<DeviceLink>("/automation/links", payload);
  return data;
}

export async function deleteDeviceLink(linkId: number) {
  const { data } = await apiClient.delete<{ ok: boolean }>(`/automation/links/${linkId}`);
  return data;
}

export interface UpdateDeviceLinkPayload {
  description?: string;
  auto_control_enabled?: boolean;
  min_value?: number | null;
  max_value?: number | null;
}

export async function updateDeviceLink(linkId: number, payload: UpdateDeviceLinkPayload) {
  const { data } = await apiClient.patch<DeviceLink>(`/automation/links/${linkId}`, payload);
  return data;
}
