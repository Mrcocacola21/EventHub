import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getTournaments } from "../api/tournaments.js";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import Input from "../components/common/Input.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import TournamentCard from "../components/tournaments/TournamentCard.jsx";
import { normalizePaginatedResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

const initialFilters = {
  status: "ALL",
  type: "ALL",
  search: "",
  page: 1,
};

const statusOptions = [
  "ALL",
  "DRAFT",
  "REGISTRATION_OPEN",
  "IN_PROGRESS",
  "FINISHED",
  "CANCELED",
];

const typeOptions = ["ALL", "SINGLE_ELIMINATION"];

function buildParams(filters) {
  const params = { page: filters.page };

  if (filters.search) params.search = filters.search;
  if (filters.status !== "ALL") params.status = filters.status;
  if (filters.type !== "ALL") params.type = filters.type;

  return params;
}

export default function TournamentsPage() {
  const [filters, setFilters] = useState(initialFilters);
  const params = useMemo(() => buildParams(filters), [filters]);

  const tournamentsQuery = useQuery({
    queryKey: queryKeys.tournaments(params),
    queryFn: () => getTournaments(params),
  });

  const response = normalizePaginatedResponse(tournamentsQuery.data);
  const tournaments = useMemo(() => {
    const search = filters.search.trim().toLowerCase();

    return response.items.filter((tournament) => {
      const statusMatches =
        filters.status === "ALL" || tournament.status === filters.status;
      const typeMatches = filters.type === "ALL" || tournament.type === filters.type;
      const searchMatches =
        !search || tournament.title.toLowerCase().includes(search);

      return statusMatches && typeMatches && searchMatches;
    });
  }, [filters, response.items]);

  function updateFilter(event) {
    setFilters((current) => ({
      ...current,
      [event.target.name]: event.target.value,
      page: 1,
    }));
  }

  function goToPage(page) {
    setFilters((current) => ({ ...current, page }));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-950">Tournaments</h1>
        <p className="mt-2 text-sm text-slate-600">
          Browse EventHub tournaments, registration state, participants, and
          brackets.
        </p>
      </div>

      <section className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 md:grid-cols-3">
        <Input
          label="Search"
          name="search"
          value={filters.search}
          onChange={updateFilter}
          placeholder="Tournament title"
        />
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Status
          </span>
          <select
            name="status"
            value={filters.status}
            onChange={updateFilter}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {status === "ALL" ? "All statuses" : status}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Type
          </span>
          <select
            name="type"
            value={filters.type}
            onChange={updateFilter}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            {typeOptions.map((type) => (
              <option key={type} value={type}>
                {type === "ALL" ? "All types" : type}
              </option>
            ))}
          </select>
        </label>
      </section>

      {tournamentsQuery.isLoading ? (
        <LoadingSpinner label="Loading tournaments" />
      ) : null}
      {tournamentsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            tournamentsQuery.error,
            "Unable to load tournaments.",
          )}
        />
      ) : null}

      {!tournamentsQuery.isLoading &&
      !tournamentsQuery.isError &&
      tournaments.length === 0 ? (
        <EmptyState
          title="No tournaments found"
          description="Try changing filters or check back after organizers create tournaments."
        />
      ) : null}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {tournaments.map((tournament) => (
          <TournamentCard key={tournament.id} tournament={tournament} />
        ))}
      </div>

      {response.isPaginated ? (
        <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>
            Page {filters.page} | {response.count} tournaments total
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => goToPage(Math.max(1, Number(filters.page) - 1))}
              disabled={!response.previous || tournamentsQuery.isLoading}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => goToPage(Number(filters.page) + 1)}
              disabled={!response.next || tournamentsQuery.isLoading}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
