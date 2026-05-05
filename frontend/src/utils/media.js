import { getBackendOrigin } from "./constants.js";

export function getMediaUrl(path) {
  if (!path) {
    return "";
  }

  if (
    path.startsWith("http://") ||
    path.startsWith("https://") ||
    path.startsWith("data:")
  ) {
    return path;
  }

  const origin = getBackendOrigin();

  if (path.startsWith("/")) {
    return `${origin}${path}`;
  }

  return `${origin}/${path}`;
}
