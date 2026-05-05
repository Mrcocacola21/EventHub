import axios from "axios";

import { API_BASE_URL, AUTH_EVENTS } from "../utils/constants.js";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
} from "../utils/tokenStorage.js";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshRequest = null;

function notifyUnauthorized() {
  clearTokens();

  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EVENTS.UNAUTHORIZED));
  }
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (config.data instanceof FormData) {
    if (typeof config.headers?.delete === "function") {
      config.headers.delete("Content-Type");
    } else if (config.headers) {
      delete config.headers["Content-Type"];
    }
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/refresh/")
    ) {
      return Promise.reject(error);
    }

    const refresh = getRefreshToken();

    if (!refresh) {
      notifyUnauthorized();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      refreshRequest =
        refreshRequest ||
        refreshClient.post("/auth/refresh/", {
          refresh,
        });

      const response = await refreshRequest;
      const access = response.data?.access;

      if (!access) {
        throw new Error("Refresh response did not include an access token.");
      }

      setAccessToken(access);
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${access}`;

      return apiClient(originalRequest);
    } catch (refreshError) {
      notifyUnauthorized();
      return Promise.reject(refreshError);
    } finally {
      refreshRequest = null;
    }
  },
);

export default apiClient;
