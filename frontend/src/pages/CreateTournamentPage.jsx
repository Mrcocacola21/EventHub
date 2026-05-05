import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { createTournament } from "../api/tournaments.js";
import Button from "../components/common/Button.jsx";
import CreateTournamentForm from "../components/tournaments/CreateTournamentForm.jsx";
import { getApiErrorMessage } from "../utils/errors.js";

export default function CreateTournamentPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [apiError, setApiError] = useState("");

  const createMutation = useMutation({
    mutationFn: createTournament,
    onSuccess: async (tournament) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tournaments"] }),
        queryClient.invalidateQueries({ queryKey: ["organizerTournaments"] }),
      ]);
      navigate(`/organizer/tournaments/${tournament.id}/manage`, {
        replace: true,
      });
    },
  });

  async function handleSubmit(payload) {
    setApiError("");

    try {
      await createMutation.mutateAsync(payload);
    } catch (requestError) {
      setApiError(
        getApiErrorMessage(requestError, "Unable to create tournament."),
      );
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Create Tournament
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Create a tournament for a published event. Bracket generation
            happens when the tournament starts.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={() => navigate("/organizer/tournaments")}
        >
          Back to tournaments
        </Button>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <CreateTournamentForm
          onSubmit={handleSubmit}
          isSubmitting={createMutation.isPending}
          apiError={apiError}
        />
      </section>
    </div>
  );
}
