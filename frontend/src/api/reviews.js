import apiClient from "./client.js";

export async function getReview(id) {
  const { data } = await apiClient.get(`/reviews/${id}/`);
  return data;
}

export async function updateReview(id, payload) {
  const { data } = await apiClient.patch(`/reviews/${id}/`, payload);
  return data;
}

export async function deleteReview(id) {
  await apiClient.delete(`/reviews/${id}/`);
}
