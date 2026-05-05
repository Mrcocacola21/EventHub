import apiClient from "./client.js";

export async function register(payload) {
  const { data } = await apiClient.post("/auth/register/", payload);
  return data;
}

export async function login(payload) {
  const { data } = await apiClient.post("/auth/login/", payload);
  return data;
}

export async function refreshToken(refresh) {
  const { data } = await apiClient.post("/auth/refresh/", { refresh });
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/users/me/");
  return data;
}

export async function updateMe(payload) {
  const { data } = await apiClient.patch("/users/me/", payload);
  return data;
}
