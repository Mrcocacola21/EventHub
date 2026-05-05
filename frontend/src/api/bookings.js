import { API_BASE_URL } from "../utils/constants.js";
import apiClient from "./client.js";

export async function createBooking(ticketTypeId) {
  const { data } = await apiClient.post("/bookings/", {
    ticket_type_id: ticketTypeId,
  });
  return data;
}

export async function getMyBookings(params) {
  const { data } = await apiClient.get("/bookings/my/", { params });
  return data;
}

export async function getBookings(params) {
  const { data } = await apiClient.get("/bookings/", { params });
  return data;
}

export async function getBooking(id) {
  const { data } = await apiClient.get(`/bookings/${id}/`);
  return data;
}

export async function cancelBooking(id) {
  const { data } = await apiClient.post(`/bookings/${id}/cancel/`);
  return data;
}

export async function useBooking(id) {
  const { data } = await apiClient.post(`/bookings/${id}/use/`);
  return data;
}

export function getPdfDownloadUrl(id) {
  return `${API_BASE_URL}/bookings/${id}/download-pdf/`;
}

export async function downloadBookingPdf(id) {
  const { data } = await apiClient.get(`/bookings/${id}/download-pdf/`, {
    responseType: "blob",
  });
  return data;
}
