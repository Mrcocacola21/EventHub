export function getParticipantName(participant) {
  if (!participant) {
    return "TBD";
  }

  return (
    participant.user_detail?.username ||
    participant.user_detail?.email ||
    participant.user ||
    `Participant #${participant.id}`
  );
}

export function getParticipantEmail(participant) {
  return participant?.user_detail?.email || "";
}

export function isCurrentUserParticipant(participants = [], user) {
  if (!user) {
    return false;
  }

  return participants.some((participant) => {
    const participantUserId = participant.user_detail?.id || participant.user;
    return String(participantUserId) === String(user.id);
  });
}

export function canRegisterForTournament(tournament) {
  return (
    tournament?.is_registration_open ||
    String(tournament?.status || "").toUpperCase() === "REGISTRATION_OPEN"
  );
}

export function getTournamentEventTitle(tournament) {
  return tournament?.event_detail?.title || "Linked event";
}
