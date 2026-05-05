import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getCategories, getEvents } from "../api/events.js";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import EventCard from "../components/events/EventCard.jsx";
import EventFilters from "../components/events/EventFilters.jsx";
import Button from "../components/common/Button.jsx";
import {
  getListFromResponse,
  normalizePaginatedResponse,
} from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

const initialFilters = {
  search: "",
  category: "",
  location: "",
  ordering: "start_datetime",
  page: 1,
};

function buildEventParams(filters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== "" && value !== null),
  );
}

export default function EventsPage() {
  const [filters, setFilters] = useState(initialFilters);
  const eventParams = useMemo(() => buildEventParams(filters), [filters]);

  const categoriesQuery = useQuery({
    queryKey: queryKeys.categories,
    queryFn: getCategories,
  });

  const { data, isError, error, isLoading } = useQuery({
    queryKey: queryKeys.events(eventParams),
    queryFn: () => getEvents(eventParams),
  });

  const categories = getListFromResponse(categoriesQuery.data);
  const paginatedEvents = normalizePaginatedResponse(data);
  const events = paginatedEvents.items;

  function goToPage(page) {
    setFilters((current) => ({
      ...current,
      page,
    }));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-950">Events</h1>
        <p className="mt-2 text-sm text-slate-600">
          Find public EventHub events by category, location, title, or date.
        </p>
      </div>

      <EventFilters
        filters={filters}
        categories={categories}
        onChange={setFilters}
        onReset={() => setFilters(initialFilters)}
      />

      {categoriesQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            categoriesQuery.error,
            "Unable to load categories.",
          )}
        />
      ) : null}

      {isLoading ? <LoadingSpinner label="Loading events" /> : null}
      {isError ? (
        <ErrorMessage
          message={getApiErrorMessage(error, "Unable to load events.")}
        />
      ) : null}

      {!isLoading && !isError && events.length === 0 ? (
        <EmptyState
          title="No events yet"
          description="Published events will appear here once the backend has data."
        />
      ) : null}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {events.map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
      </div>

      {paginatedEvents.isPaginated ? (
        <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>
            Page {filters.page} | {paginatedEvents.count} events total
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => goToPage(Math.max(1, Number(filters.page) - 1))}
              disabled={!paginatedEvents.previous || isLoading}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => goToPage(Number(filters.page) + 1)}
              disabled={!paginatedEvents.next || isLoading}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
