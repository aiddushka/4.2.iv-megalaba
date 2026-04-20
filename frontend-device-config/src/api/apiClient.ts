import axios from "axios";

export const apiClient = axios.create({
  baseURL: "https://localhost:8443",
  headers: {
    "Content-Type": "application/json",
  },
});

