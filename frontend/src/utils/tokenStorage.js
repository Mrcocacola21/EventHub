const ACCESS_TOKEN_KEY = "eventhub.access_token";
const REFRESH_TOKEN_KEY = "eventhub.refresh_token";

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function getAccessToken() {
  return getStorage()?.getItem(ACCESS_TOKEN_KEY) || null;
}

export function getRefreshToken() {
  return getStorage()?.getItem(REFRESH_TOKEN_KEY) || null;
}

export function setAccessToken(accessToken) {
  const storage = getStorage();

  if (!storage || !accessToken) {
    return;
  }

  storage.setItem(ACCESS_TOKEN_KEY, accessToken);
}

export function setRefreshToken(refreshToken) {
  const storage = getStorage();

  if (!storage || !refreshToken) {
    return;
  }

  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function setTokens({ access, refresh } = {}) {
  if (access) {
    setAccessToken(access);
  }

  if (refresh) {
    setRefreshToken(refresh);
  }
}

export function clearTokens() {
  const storage = getStorage();

  if (!storage) {
    return;
  }

  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasStoredAccessToken() {
  return Boolean(getAccessToken());
}
