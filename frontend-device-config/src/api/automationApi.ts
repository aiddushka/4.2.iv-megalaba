import { apiClient } from "./apiClient";

export interface CreateDeviceLinkPayload {
  source_device_uid: string;
  target_device_uid: string;
  controller?: string;
  description?: string;
  active?: boolean;
}

export async function createDeviceLink(payload: CreateDeviceLinkPayload) {
  const { data } = await apiClient.post("/automation/links", payload);
  return data;
}
