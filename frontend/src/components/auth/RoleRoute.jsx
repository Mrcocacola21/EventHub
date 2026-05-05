import { Navigate, useLocation } from "react-router-dom";

import { USER_ROLES } from "../../utils/constants.js";
import LoadingSpinner from "../common/LoadingSpinner.jsx";
import { useAuth } from "../../hooks/useAuth.js";

export default function RoleRoute({ allowedRoles = [], children }) {
  const location = useLocation();
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <LoadingSpinner label="Checking permissions" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const isAllowed =
    user?.role === USER_ROLES.ADMIN || allowedRoles.includes(user?.role);

  if (!isAllowed) {
    return <Navigate to="/403" replace />;
  }

  return children;
}
