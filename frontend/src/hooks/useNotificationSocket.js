import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "./useAuth.js";
import { WS_BASE_URL } from "../utils/constants.js";
import { queryKeys } from "../utils/queryKeys.js";
import { getAccessToken } from "../utils/tokenStorage.js";

const TOURNAMENT_NOTIFICATION_TYPES = new Set([
  "TOURNAMENT_STARTED",
  "MATCH_STARTED",
  "MATCH_RESULT_UPDATED",
  "TOURNAMENT_FINISHED",
]);

function buildNotificationSocketUrl(token) {
  const base = WS_BASE_URL.replace(/\/$/, "");
  return `${base}/notifications/?token=${encodeURIComponent(token)}`;
}

export function useNotificationSocket() {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getAccessToken();

    if (!isAuthenticated || !token) {
      setIsConnected(false);
      return undefined;
    }

    shouldReconnectRef.current = true;

    function invalidateTournamentData(notification) {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });

      if (!TOURNAMENT_NOTIFICATION_TYPES.has(notification?.type)) {
        return;
      }

      const tournamentId =
        notification?.metadata?.tournament_id ||
        (notification?.entity_type === "Tournament"
          ? notification?.entity_id
          : null);

      queryClient.invalidateQueries({ queryKey: ["tournaments"] });
      queryClient.invalidateQueries({ queryKey: ["organizerTournaments"] });

      if (tournamentId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournament(tournamentId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentParticipants(tournamentId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentMatches(tournamentId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentBracket(tournamentId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ["tournament"] });
        queryClient.invalidateQueries({ queryKey: ["tournamentParticipants"] });
        queryClient.invalidateQueries({ queryKey: ["tournamentMatches"] });
        queryClient.invalidateQueries({ queryKey: ["tournamentBracket"] });
      }
    }

    function connect() {
      const socket = new WebSocket(buildNotificationSocketUrl(token));
      socketRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setError("");
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);

          if (message.type === "notification") {
            invalidateTournamentData(message.notification);
          }
        } catch {
          setError("Unable to parse notification socket message.");
        }
      };

      socket.onerror = () => {
        setError("Notification socket error.");
      };

      socket.onclose = () => {
        setIsConnected(false);

        if (shouldReconnectRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
        }
      };
    }

    connect();

    return () => {
      shouldReconnectRef.current = false;

      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }

      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [isAuthenticated, queryClient]);

  return {
    isConnected,
    lastMessage,
    error,
  };
}
