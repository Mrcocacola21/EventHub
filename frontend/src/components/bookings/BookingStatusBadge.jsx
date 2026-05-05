import Badge from "../common/Badge.jsx";

const statusVariants = {
  PAID: "success",
  PENDING: "warning",
  CANCELED: "danger",
  CANCELLED: "danger",
  EXPIRED: "default",
};

export default function BookingStatusBadge({ status }) {
  const normalizedStatus = String(status || "UNKNOWN").toUpperCase();

  return (
    <Badge variant={statusVariants[normalizedStatus] || "default"}>
      {normalizedStatus}
    </Badge>
  );
}
