import { CalendarDays, MapPin, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { formatDateTime } from "../../utils/formatters.js";
import { getMediaUrl } from "../../utils/media.js";
import Badge from "../common/Badge.jsx";
import Button from "../common/Button.jsx";

function statusVariant(status) {
  if (status === "PUBLISHED") {
    return "success";
  }

  if (status === "CANCELED") {
    return "danger";
  }

  if (status === "FINISHED") {
    return "default";
  }

  return "warning";
}

export default function EventCard({ event }) {
  const category = event.category_detail?.name || event.category?.name;
  const coverImage = getMediaUrl(event.cover_image);

  return (
    <article className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:border-slate-300 hover:shadow-md">
      {coverImage ? (
        <img
          src={coverImage}
          alt=""
          className="h-44 w-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="flex h-44 items-center justify-center bg-slate-100 text-sm font-medium text-slate-500">
          EventHub
        </div>
      )}

      <div className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="line-clamp-2 text-lg font-semibold text-slate-950">
              {event.title}
            </h2>
            {category ? (
              <p className="mt-1 text-sm text-slate-500">{category}</p>
            ) : null}
          </div>
          <Badge variant={statusVariant(event.status)}>{event.status}</Badge>
        </div>

        <div className="space-y-2 text-sm text-slate-600">
          <p className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-slate-400" aria-hidden="true" />
            {event.location || "Location TBD"}
          </p>
          <p className="flex items-center gap-2">
            <CalendarDays
              className="h-4 w-4 text-slate-400"
              aria-hidden="true"
            />
            {formatDateTime(event.start_datetime)}
          </p>
          {event.average_rating !== null && event.average_rating !== undefined ? (
            <p className="flex items-center gap-2">
              <Star className="h-4 w-4 text-amber-500" aria-hidden="true" />
              {event.average_rating} ({event.reviews_count || 0} reviews)
            </p>
          ) : null}
        </div>

        <Button as={Link} to={`/events/${event.id}`} variant="secondary">
          View details
        </Button>
      </div>
    </article>
  );
}
