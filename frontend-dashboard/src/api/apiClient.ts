import axios from "axios";
import { getStoredToken, clearStoredToken } from "./authApi";

export const apiClient = axios.create({
  baseURL: "https://localhost:8443",
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStoredToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

