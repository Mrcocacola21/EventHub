import { CheckCircle } from "lucide-react";

import { getBookingEventId, getBookingTicketName } from "../../utils/bookings.js";
import { formatDateTime, formatPrice } from "../../utils/formatters.js";
import BookingStatusBadge from "../bookings/BookingStatusBadge.jsx";
import PdfDownloadButton from "../bookings/PdfDownloadButton.jsx";
import Button from "../common/Button.jsx";

export default function BookingTable({
  bookings = [],
  eventId,
  onUse,
  usingId,
}) {
  const eventBookings = bookings.filter((booking) => {
    const bookingEventId = getBookingEventId(booking);
    return !eventId || String(bookingEventId) === String(eventId);
  });

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Booking</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Ticket</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Used</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {eventBookings.map((booking) => {
              const canUse =
                String(booking.status).toUpperCase() === "PAID" &&
                !booking.is_used;

              return (
                <tr key={booking.id} className="align-top">
                  <td className="px-4 py-4 font-medium text-slate-950">
                    #{booking.id}
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {booking.user_detail?.email || booking.user || "User"}
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {getBookingTicketName(booking)}
                  </td>
                  <td className="px-4 py-4">
                    <BookingStatusBadge status={booking.status} />
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {formatPrice(booking.price_at_purchase)}
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {booking.is_used
                      ? formatDateTime(booking.used_at)
                      : "Not used"}
                  </td>
                  <td className="px-4 py-4 text-slate-600">
                    {formatDateTime(booking.created_at)}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      <PdfDownloadButton bookingId={booking.id} />
                      {canUse ? (
                        <Button
                          size="sm"
                          onClick={() => onUse(booking)}
                          disabled={usingId === booking.id}
                        >
                          <CheckCircle className="h-4 w-4" aria-hidden="true" />
                          {usingId === booking.id ? "Using..." : "Use ticket"}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
