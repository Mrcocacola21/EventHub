import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { createBooking } from "../api/bookings.js";
import { getEvent, getEventTickets } from "../api/events.js";
import Badge from "../components/common/Badge.jsx";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import TicketTypeCard from "../components/tickets/TicketTypeCard.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { getListFromResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";
import { getMediaUrl } from "../utils/media.js";
import { queryKeys } from "../utils/queryKeys.js";

export default function EventDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [buyingTicketId, setBuyingTicketId] = useState(null);
  const [bookingSuccess, setBookingSuccess] = useState(null);
  const [bookingError, setBookingError] = useState("");

  const { data: event, isError, error, isLoading } = useQuery({
    queryKey: queryKeys.event(id),
    queryFn: () => getEvent(id),
    enabled: Boolean(id),
  });

  const ticketsQuery = useQuery({
    queryKey: queryKeys.eventTickets(id),
    queryFn: () => getEventTickets(id),
    enabled: Boolean(id),
  });

  const createBookingMutation = useMutation({
    mutationFn: createBooking,
    onSuccess: async (booking) => {
      setBookingSuccess(booking);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.eventTickets(id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.myBookings }),
        queryClient.invalidateQueries({ queryKey: queryKeys.event(id) }),
      ]);
    },
  });

  async function handleBuy(ticket) {
    setBookingError("");
    setBookingSuccess(null);

    if (!isAuthenticated) {
      navigate("/login", { state: { from: location } });
      return;
    }

    setBuyingTicketId(ticket.id);

    try {
      await createBookingMutation.mutateAsync(ticket.id);
    } catch (requestError) {
      setBookingError(
        getApiErrorMessage(requestError, "Unable to create booking."),
      );
    } finally {
      setBuyingTicketId(null);
    }
  }

  if (isLoading) {
    return <LoadingSpinner label="Loading event" />;
  }

  if (isError) {
    return (
      <ErrorMessage
        message={getApiErrorMessage(error, "Unable to load event details.")}
      />
    );
  }

  const tickets = getListFromResponse(ticketsQuery.data);
  const category = event?.category_detail?.name || event?.category?.name;
  const coverImage = getMediaUrl(event?.cover_image);

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {coverImage ? (
          <img
            src={coverImage}
            alt=""
            className="h-72 w-full object-cover"
          />
        ) : null}
        <div className="flex flex-col gap-4 p-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-950">
                {event?.title}
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                {category ? `${category} | ` : ""}
                {event?.location || "Location TBD"}
              </p>
            </div>
            <Badge variant="info">{event?.status || "DRAFT"}</Badge>
          </div>
          <p className="text-sm text-slate-500">
            {formatDateTime(event?.start_datetime)} to{" "}
            {formatDateTime(event?.end_datetime)}
          </p>
          <p className="max-w-3xl text-sm leading-6 text-slate-700">
            {event?.description || "No event description yet."}
          </p>
          {event?.average_rating !== null &&
          event?.average_rating !== undefined ? (
            <p className="text-sm font-medium text-slate-700">
              Rating {event.average_rating} | {event.reviews_count || 0} reviews
            </p>
          ) : null}
        </div>
      </div>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">Tickets</h2>
          <p className="mt-2 text-sm text-slate-600">
            Choose an available ticket type and EventHub will create your
            booking ticket.
          </p>
        </div>

        {bookingSuccess ? (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            Booking #{bookingSuccess.id} created.{" "}
            <Link
              to={`/bookings/${bookingSuccess.id}`}
              className="font-semibold underline"
            >
              View ticket details
            </Link>
          </div>
        ) : null}
        <ErrorMessage message={bookingError} />

        {ticketsQuery.isLoading ? (
          <LoadingSpinner label="Loading ticket types" />
        ) : null}
        {ticketsQuery.isError ? (
          <ErrorMessage
            message={getApiErrorMessage(
              ticketsQuery.error,
              "Unable to load ticket types.",
            )}
          />
        ) : null}

        {!ticketsQuery.isLoading &&
        !ticketsQuery.isError &&
        tickets.length === 0 ? (
          <EmptyState
            title="No tickets available"
            description="Ticket types will appear here when sales are configured."
          />
        ) : null}

        <div className="grid gap-4">
          {tickets.map((ticket) => (
            <TicketTypeCard
              key={ticket.id}
              ticket={ticket}
              onBuy={handleBuy}
              isBuying={buyingTicketId === ticket.id}
              isAuthenticated={isAuthenticated}
            />
          ))}
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-slate-950">Reviews</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Full reviews UI is intentionally left for a later stage. Aggregate
            rating is displayed above when available.
          </p>
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-slate-950">Booking notes</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Ticket ownership, QR code, PDF ticket, status, and final price are
            controlled by the backend.
          </p>
        </section>
      </div>

      <Button as={Link} to="/events" variant="secondary">
        Back to events
      </Button>
    </div>
  );
}
