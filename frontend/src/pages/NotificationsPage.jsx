import Badge from "../components/common/Badge.jsx";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import { useNotifications } from "../hooks/useNotifications.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";

export default function NotificationsPage() {
  const {
    notifications,
    isLoading,
    isError,
    error,
    markRead,
    markAllRead,
    isMarkingAllRead,
  } = useNotifications();

  const unreadCount = notifications.filter((item) => !item.is_read).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Notifications
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            HTTP notification list with basic read actions.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => markAllRead()}
          disabled={isMarkingAllRead || unreadCount === 0}
        >
          {isMarkingAllRead ? "Marking..." : "Mark all read"}
        </Button>
      </div>

      {isLoading ? <LoadingSpinner label="Loading notifications" /> : null}
      {isError ? (
        <ErrorMessage
          message={getApiErrorMessage(error, "Unable to load notifications.")}
        />
      ) : null}

      {!isLoading && !isError && notifications.length === 0 ? (
        <EmptyState
          title="No notifications"
          description="Booking, event, and tournament notifications will appear here."
        />
      ) : null}

      <div className="grid gap-4">
        {notifications.map((notification) => (
          <article
            key={notification.id}
            className="rounded-lg border border-slate-200 bg-white p-5"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-950">
                  {notification.title}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {notification.message}
                </p>
                <p className="mt-3 text-xs text-slate-500">
                  {formatDateTime(notification.created_at)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant={notification.is_read ? "default" : "info"}>
                  {notification.is_read ? "Read" : "Unread"}
                </Badge>
                {!notification.is_read ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => markRead(notification.id)}
                  >
                    Mark read
                  </Button>
                ) : null}
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
