import { Eye, XCircle } from "lucide-react";
import { Link } from "react-router-dom";

import {
  canCancelBooking,
  getBookingEventTitle,
  getBookingTicketName,
} from "../../utils/bookings.js";
import { formatDateTime, formatPrice } from "../../utils/formatters.js";
import Button from "../common/Button.jsx";
import BookingStatusBadge from "./BookingStatusBadge.jsx";
import PdfDownloadButton from "./PdfDownloadButton.jsx";

export default function BookingCard({ booking, onCancel, isCanceling = false }) {
  const canCancel = canCancelBooking(booking);

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">
            {getBookingEventTitle(booking)}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {getBookingTicketName(booking)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <BookingStatusBadge status={booking.status} />
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
            {booking.is_used ? "Used" : "Unused"}
          </span>
        </div>
      </div>

      <dl className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Price</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {formatPrice(booking.price_at_purchase)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Created</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {formatDateTime(booking.created_at)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Booking ID</dt>
          <dd className="mt-1 font-medium text-slate-950">#{booking.id}</dd>
        </div>
      </dl>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button as={Link} to={`/bookings/${booking.id}`} size="sm">
          <Eye className="h-4 w-4" aria-hidden="true" />
          Details
        </Button>
        <PdfDownloadButton bookingId={booking.id} />
        {canCancel ? (
          <Button
            size="sm"
            variant="danger"
            onClick={() => onCancel?.(booking)}
            disabled={isCanceling}
          >
            <XCircle className="h-4 w-4" aria-hidden="true" />
            {isCanceling ? "Canceling..." : "Cancel"}
          </Button>
        ) : null}
      </div>
    </article>
  );
}
