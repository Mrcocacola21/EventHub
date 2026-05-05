import apiClient from "./client.js";

export async function getTournaments(params) {
  const { data } = await apiClient.get("/tournaments/", { params });
  return data;
}

export async function getTournament(id) {
  const { data } = await apiClient.get(`/tournaments/${id}/`);
  return data;
}

export async function createTournament(payload) {
  const { data } = await apiClient.post("/tournaments/", payload);
  return data;
}

export async function updateTournament(id, payload) {
  const { data } = await apiClient.patch(`/tournaments/${id}/`, payload);
  return data;
}

export async function deleteTournament(id) {
  await apiClient.delete(`/tournaments/${id}/`);
}

export async function openTournamentRegistration(id) {
  const { data } = await apiClient.post(
    `/tournaments/${id}/open-registration/`,
  );
  return data;
}

export async function cancelTournament(id) {
  const { data } = await apiClient.post(`/tournaments/${id}/cancel/`);
  return data;
}

export async function registerForTournament(id) {
  const { data } = await apiClient.post(`/tournaments/${id}/register/`);
  return data;
}

export async function startTournament(id) {
  const { data } = await apiClient.post(`/tournaments/${id}/start/`);
  return data;
}

export async function getTournamentBracket(id) {
  const { data } = await apiClient.get(`/tournaments/${id}/bracket/`);
  return data;
}

export async function getTournamentParticipants(id) {
  const { data } = await apiClient.get(`/tournaments/${id}/participants/`);
  return data;
}

export async function addTournamentParticipant(id, userId) {
  const payload = userId ? { user: userId } : {};
  const { data } = await apiClient.post(
    `/tournaments/${id}/participants/`,
    payload,
  );
  return data;
}

export async function getTournamentMatches(id) {
  const { data } = await apiClient.get(`/tournaments/${id}/matches/`);
  return data;
}

export async function getMatch(id) {
  const { data } = await apiClient.get(`/matches/${id}/`);
  return data;
}

export async function submitMatchResult(matchId, winnerId) {
  const { data } = await apiClient.post(`/matches/${matchId}/result/`, {
    winner_id: winnerId,
  });
  return data;
}
