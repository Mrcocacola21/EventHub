import apiClient from "./client.js";

export async function getCurrentUser() {
  const { data } = await apiClient.get("/users/me/");
  return data;
}

export async function updateCurrentUser(payload) {
  const { data } = await apiClient.patch("/users/me/", payload);
  return data;
}
