import {
  Bell,
  LayoutDashboard,
  ScanLine,
  Ticket,
  Trophy,
  User,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { USER_ROLES } from "../../utils/constants.js";
import { useAuth } from "../../hooks/useAuth.js";

function linkClass({ isActive }) {
  return [
    "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-slate-900 text-white"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
  ].join(" ");
}

export default function Sidebar() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  const canManage =
    user?.role === USER_ROLES.ORGANIZER || user?.role === USER_ROLES.ADMIN;

  return (
    <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white px-4 py-6 lg:block">
      <p className="px-3 text-xs font-semibold uppercase text-slate-400">
        Workspace
      </p>
      <nav className="mt-3 space-y-1">
        <NavLink to="/profile" className={linkClass}>
          <User className="h-4 w-4" aria-hidden="true" />
          Profile
        </NavLink>
        <NavLink to="/bookings" className={linkClass}>
          <Ticket className="h-4 w-4" aria-hidden="true" />
          My Bookings
        </NavLink>
        <NavLink to="/notifications" className={linkClass}>
          <Bell className="h-4 w-4" aria-hidden="true" />
          Notifications
        </NavLink>
        {canManage ? (
          <>
            <NavLink to="/organizer" className={linkClass}>
              <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
              Organizer Dashboard
            </NavLink>
            <NavLink to="/organizer/qr-check" className={linkClass}>
              <ScanLine className="h-4 w-4" aria-hidden="true" />
              QR Check
            </NavLink>
            <NavLink to="/organizer/tournaments" className={linkClass}>
              <Trophy className="h-4 w-4" aria-hidden="true" />
              Tournaments
            </NavLink>
          </>
        ) : null}
      </nav>
    </aside>
  );
}
