export function canCancelBooking(booking) {
  return (
    booking &&
    !booking.is_used &&
    ["PAID", "PENDING"].includes(String(booking.status || "").toUpperCase())
  );
}

export function getBookingEventSummary(booking) {
  return (
    booking?.event ||
    booking?.ticket_type_detail?.event ||
    booking?.ticket_type?.event ||
    null
  );
}

export function getBookingEventTitle(booking) {
  return getBookingEventSummary(booking)?.title || "Event";
}

export function getBookingEventId(booking) {
  return getBookingEventSummary(booking)?.id || null;
}

export function getBookingTicketName(booking) {
  return booking?.ticket_type_detail?.name || booking?.ticket_type?.name || "Ticket";
}
