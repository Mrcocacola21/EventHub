import Badge from "../common/Badge.jsx";

const variants = {
  DRAFT: "warning",
  REGISTRATION_OPEN: "info",
  IN_PROGRESS: "success",
  FINISHED: "default",
  CANCELED: "danger",
};

export default function TournamentStatusBadge({ status }) {
  const normalizedStatus = String(status || "DRAFT").toUpperCase();

  return (
    <Badge variant={variants[normalizedStatus] || "default"}>
      {normalizedStatus}
    </Badge>
  );
}
