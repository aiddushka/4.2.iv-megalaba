import { apiClient } from "./apiClient";

const TOKEN_KEY = "greenhouse_token";

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  can_view_dashboard: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);
  const { data } = await apiClient.post<TokenResponse>("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function register(username: string, password: string): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/register", { username, password });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}
