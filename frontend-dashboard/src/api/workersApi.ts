import { apiClient } from "./apiClient";

export interface Worker {
  id: number;
  username: string;
  is_admin: boolean;
  can_view_dashboard: boolean;
}

export async function fetchWorkers(): Promise<Worker[]> {
  const { data } = await apiClient.get<Worker[]>("/auth/workers");
  return data;
}

export async function setDashboardAccess(
  userId: number,
  canViewDashboard: boolean
): Promise<Worker> {
  const { data } = await apiClient.patch<Worker>(
    `/auth/workers/${userId}/dashboard-access`,
    { can_view_dashboard: canViewDashboard }
  );
  return data;
}
