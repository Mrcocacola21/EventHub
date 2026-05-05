import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getMe,
  login as loginRequest,
  register as registerRequest,
  updateMe,
} from "../api/auth.js";
import { AUTH_EVENTS, USER_ROLES } from "../utils/constants.js";
import {
  clearTokens,
  getAccessToken,
  setTokens,
} from "../utils/tokenStorage.js";

const AuthContext = createContext(null);

function persistAuthPayload(payload) {
  setTokens({
    access: payload?.access,
    refresh: payload?.refresh,
  });
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      return null;
    }

    const currentUser = await getMe();
    setUser(currentUser);
    return currentUser;
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function bootstrapSession() {
      if (!getAccessToken()) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await getMe();

        if (isMounted) {
          setUser(currentUser);
        }
      } catch {
        clearTokens();

        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    bootstrapSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      clearTokens();
      setUser(null);
    }

    window.addEventListener(AUTH_EVENTS.UNAUTHORIZED, handleUnauthorized);

    return () => {
      window.removeEventListener(AUTH_EVENTS.UNAUTHORIZED, handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const payload = await loginRequest({ email, password });
    persistAuthPayload(payload);

    const nextUser = payload.user || (await getMe());
    setUser(nextUser);
    return nextUser;
  }, []);

  const register = useCallback(async (payload) => {
    const response = await registerRequest(payload);
    persistAuthPayload(response);

    const nextUser = response.user || (await getMe());
    setUser(nextUser);
    return nextUser;
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);

    window.dispatchEvent(new Event(AUTH_EVENTS.LOGOUT));
  }, []);

  const updateProfile = useCallback(async (payload) => {
    const updatedUser = await updateMe(payload);
    setUser(updatedUser);
    return updatedUser;
  }, []);

  const hasRole = useCallback(
    (role) => {
      return user?.role === role;
    },
    [user],
  );

  const value = useMemo(() => {
    const isAdmin = user?.role === USER_ROLES.ADMIN;
    const isOrganizer = user?.role === USER_ROLES.ORGANIZER;

    return {
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      refreshUser,
      updateProfile,
      hasRole,
      isOrganizer,
      isAdmin,
    };
  }, [
    hasRole,
    isLoading,
    login,
    logout,
    refreshUser,
    register,
    updateProfile,
    user,
  ]);

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}
