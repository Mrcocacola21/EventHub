import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "../components/auth/ProtectedRoute.jsx";
import RoleRoute from "../components/auth/RoleRoute.jsx";
import AppLayout from "../components/layout/AppLayout.jsx";
import HomePage from "../pages/HomePage.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import RegisterPage from "../pages/RegisterPage.jsx";
import ProfilePage from "../pages/ProfilePage.jsx";
import EventsPage from "../pages/EventsPage.jsx";
import EventDetailsPage from "../pages/EventDetailsPage.jsx";
import MyBookingsPage from "../pages/MyBookingsPage.jsx";
import BookingDetailsPage from "../pages/BookingDetailsPage.jsx";
import OrganizerDashboardPage from "../pages/OrganizerDashboardPage.jsx";
import CreateEventPage from "../pages/CreateEventPage.jsx";
import EditEventPage from "../pages/EditEventPage.jsx";
import ManageTicketsPage from "../pages/ManageTicketsPage.jsx";
import EventBookingsPage from "../pages/EventBookingsPage.jsx";
import QrCheckPage from "../pages/QrCheckPage.jsx";
import OrganizerTournamentsPage from "../pages/OrganizerTournamentsPage.jsx";
import CreateTournamentPage from "../pages/CreateTournamentPage.jsx";
import ManageTournamentPage from "../pages/ManageTournamentPage.jsx";
import TournamentsPage from "../pages/TournamentsPage.jsx";
import TournamentDetailsPage from "../pages/TournamentDetailsPage.jsx";
import NotificationsPage from "../pages/NotificationsPage.jsx";
import ForbiddenPage from "../pages/ForbiddenPage.jsx";
import NotFoundPage from "../pages/NotFoundPage.jsx";
import { USER_ROLES } from "../utils/constants.js";

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="events" element={<EventsPage />} />
        <Route path="events/:id" element={<EventDetailsPage />} />
        <Route path="tournaments" element={<TournamentsPage />} />
        <Route path="tournaments/:id" element={<TournamentDetailsPage />} />
        <Route path="403" element={<ForbiddenPage />} />

        <Route
          path="profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="bookings"
          element={
            <ProtectedRoute>
              <MyBookingsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="bookings/:id"
          element={
            <ProtectedRoute>
              <BookingDetailsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="notifications"
          element={
            <ProtectedRoute>
              <NotificationsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="organizer"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <OrganizerDashboardPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/events/new"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <CreateEventPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/events/:id/edit"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <EditEventPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/events/:id/tickets"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <ManageTicketsPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/events/:id/bookings"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <EventBookingsPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/qr-check"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <QrCheckPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/tournaments"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <OrganizerTournamentsPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/tournaments/new"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <CreateTournamentPage />
            </RoleRoute>
          }
        />
        <Route
          path="organizer/tournaments/:id/manage"
          element={
            <RoleRoute allowedRoles={[USER_ROLES.ORGANIZER]}>
              <ManageTournamentPage />
            </RoleRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
