export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000/ws";

export function getBackendOrigin() {
  if (API_BASE_URL.startsWith("/")) {
    return typeof window !== "undefined" ? window.location.origin : "";
  }

  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return API_BASE_URL.replace(/\/api\/?$/, "");
  }
}

export const USER_ROLES = Object.freeze({
  USER: "USER",
  ORGANIZER: "ORGANIZER",
  ADMIN: "ADMIN",
});

export const AUTH_EVENTS = Object.freeze({
  UNAUTHORIZED: "eventhub:auth:unauthorized",
  LOGOUT: "eventhub:auth:logout",
});
