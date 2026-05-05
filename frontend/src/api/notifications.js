import apiClient from "./client.js";

export async function getNotifications(params) {
  const { data } = await apiClient.get("/notifications/", { params });
  return data;
}

export async function markNotificationRead(id) {
  const { data } = await apiClient.post(`/notifications/${id}/read/`);
  return data;
}

export async function markAllNotificationsRead() {
  const { data } = await apiClient.post("/notifications/read-all/");
  return data;
}
