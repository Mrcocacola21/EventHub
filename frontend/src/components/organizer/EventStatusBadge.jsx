import Badge from "../common/Badge.jsx";

const variants = {
  DRAFT: "warning",
  PUBLISHED: "success",
  CANCELED: "danger",
  FINISHED: "default",
};

export default function EventStatusBadge({ status }) {
  const normalizedStatus = String(status || "DRAFT").toUpperCase();

  return (
    <Badge variant={variants[normalizedStatus] || "default"}>
      {normalizedStatus}
    </Badge>
  );
}
