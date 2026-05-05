import {
  Bell,
  CalendarDays,
  LogOut,
  ScanLine,
  ShieldCheck,
  Ticket,
  Trophy,
  User,
} from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import Button from "../common/Button.jsx";
import { USER_ROLES } from "../../utils/constants.js";
import { useAuth } from "../../hooks/useAuth.js";

function navClass({ isActive }) {
  return [
    "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-slate-950 text-white"
      : "text-slate-700 hover:bg-slate-100 hover:text-slate-950",
  ].join(" ");
}

export default function Header() {
  const navigate = useNavigate();
  const { isAuthenticated, logout, user } = useAuth();
  const canManage =
    user?.role === USER_ROLES.ORGANIZER || user?.role === USER_ROLES.ADMIN;

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-lg font-semibold text-slate-950"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-950 text-sm font-bold text-white">
            EH
          </span>
          EventHub
        </Link>

        <nav className="flex flex-wrap items-center gap-1">
          <NavLink to="/events" className={navClass}>
            <CalendarDays className="h-4 w-4" aria-hidden="true" />
            Events
          </NavLink>
          <NavLink to="/tournaments" className={navClass}>
            <Trophy className="h-4 w-4" aria-hidden="true" />
            Tournaments
          </NavLink>

          {isAuthenticated ? (
            <>
              <NavLink to="/bookings" className={navClass}>
                <Ticket className="h-4 w-4" aria-hidden="true" />
                My Bookings
              </NavLink>
              <NavLink to="/notifications" className={navClass}>
                <Bell className="h-4 w-4" aria-hidden="true" />
                Notifications
              </NavLink>
              {canManage ? (
                <>
                  <NavLink to="/organizer" className={navClass}>
                    <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                    Organizer
                  </NavLink>
                  <NavLink to="/organizer/qr-check" className={navClass}>
                    <ScanLine className="h-4 w-4" aria-hidden="true" />
                    QR Check
                  </NavLink>
                  <NavLink to="/organizer/tournaments" className={navClass}>
                    <Trophy className="h-4 w-4" aria-hidden="true" />
                    Manage Tournaments
                  </NavLink>
                </>
              ) : null}
              <NavLink to="/profile" className={navClass}>
                <User className="h-4 w-4" aria-hidden="true" />
                Profile
              </NavLink>
              <Button variant="ghost" onClick={handleLogout}>
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Logout
              </Button>
            </>
          ) : (
            <>
              <Button as={Link} to="/login" variant="ghost">
                Login
              </Button>
              <Button as={Link} to="/register" variant="primary">
                Register
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
