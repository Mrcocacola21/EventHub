import apiClient from "./client.js";

export async function getEvents(params) {
  const { data } = await apiClient.get("/events/", { params });
  return data;
}

export async function getPopularEvents(params) {
  const { data } = await apiClient.get("/events/popular/", { params });
  return data;
}

export async function getEvent(id) {
  const { data } = await apiClient.get(`/events/${id}/`);
  return data;
}

export async function getCategories() {
  const { data } = await apiClient.get("/event-categories/");
  return data;
}

export async function createEvent(payload) {
  const { data } = await apiClient.post("/events/", payload);
  return data;
}

export async function updateEvent(id, payload) {
  const { data } = await apiClient.patch(`/events/${id}/`, payload);
  return data;
}

export async function deleteEvent(id) {
  await apiClient.delete(`/events/${id}/`);
}

export async function publishEvent(id) {
  const { data } = await apiClient.post(`/events/${id}/publish/`);
  return data;
}

export async function cancelEvent(id) {
  const { data } = await apiClient.post(`/events/${id}/cancel/`);
  return data;
}

export async function finishEvent(id) {
  const { data } = await apiClient.post(`/events/${id}/finish/`);
  return data;
}

export async function getEventTickets(eventId) {
  const { data } = await apiClient.get(`/events/${eventId}/tickets/`);
  return data;
}

export async function createEventTicket(eventId, payload) {
  const { data } = await apiClient.post(`/events/${eventId}/tickets/`, payload);
  return data;
}

export async function getTicketType(id) {
  const { data } = await apiClient.get(`/ticket-types/${id}/`);
  return data;
}

export async function updateTicketType(id, payload) {
  const { data } = await apiClient.patch(`/ticket-types/${id}/`, payload);
  return data;
}

export async function deleteTicketType(id) {
  await apiClient.delete(`/ticket-types/${id}/`);
}

export async function getEventReviews(eventId) {
  const { data } = await apiClient.get(`/events/${eventId}/reviews/`);
  return data;
}

export async function createEventReview(eventId, payload) {
  const { data } = await apiClient.post(`/events/${eventId}/reviews/`, payload);
  return data;
}
