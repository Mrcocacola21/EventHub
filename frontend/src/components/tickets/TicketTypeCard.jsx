import { LogIn, ShoppingCart } from "lucide-react";

import { formatDateTime, formatPrice } from "../../utils/formatters.js";
import Badge from "../common/Badge.jsx";
import Button from "../common/Button.jsx";

function ticketAvailabilityText(ticket) {
  if (ticket.is_sold_out) {
    return "Sold out";
  }

  if (!ticket.is_active) {
    return "Inactive";
  }

  if (!ticket.is_sales_period_active) {
    return "Sales closed";
  }

  if (!ticket.is_available_for_purchase) {
    return "Unavailable";
  }

  return "Available";
}

export default function TicketTypeCard({
  ticket,
  onBuy,
  isBuying = false,
  isAuthenticated = false,
}) {
  const isAvailable = Boolean(ticket.is_available_for_purchase);

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">
            {ticket.name}
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {ticket.description || "No ticket description."}
          </p>
        </div>
        <div className="text-left md:text-right">
          <p className="text-xl font-semibold text-slate-950">
            {formatPrice(ticket.price)}
          </p>
          <Badge variant={isAvailable ? "success" : "default"}>
            {ticketAvailabilityText(ticket)}
          </Badge>
        </div>
      </div>

      <dl className="mt-5 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Available</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {ticket.available_quantity ?? "TBD"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Sales start</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {formatDateTime(ticket.sales_start)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Sales end</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {formatDateTime(ticket.sales_end)}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <Button
          onClick={() => onBuy?.(ticket)}
          disabled={!isAvailable || isBuying}
        >
          {isAuthenticated ? (
            <ShoppingCart className="h-4 w-4" aria-hidden="true" />
          ) : (
            <LogIn className="h-4 w-4" aria-hidden="true" />
          )}
          {isAuthenticated
            ? !isAvailable
              ? "Unavailable"
              : isBuying
              ? "Booking..."
              : "Buy ticket"
            : isAvailable
              ? "Login to buy"
              : "Unavailable"}
        </Button>
      </div>
    </article>
  );
}
